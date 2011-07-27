#!/usr/bin/python
#
# Pulp Registration and subscription module
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import base64
import os
import re

import string
import sys
import time
from gettext import gettext as _
from optparse import OptionGroup

from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api.consumergroup import ConsumerGroupAPI
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.file import FileAPI
from pulp.client.api.job import JobAPI
from pulp.client.api.package import PackageAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.api.upload import UploadAPI
from pulp.client.constants import UNAVAILABLE, PACKAGE_INFO
from pulp.client.core.utils import (
    print_header, parse_at_schedule, 
    waitinit, printwait, askwait, askcontinue,
    task_end, task_succeeded, job_end, job_succeeded)
from pulp.client.lib import utils
from pulp.client.pluginlib.command import Action, Command
from pulp.client.lib.logutil import getLogger


log = getLogger(__name__)


# package action base class ---------------------------------------------------

class PackageAction(Action):

    def __init__(self, cfg):
        super(PackageAction, self).__init__(cfg)
        self.consumer_api = ConsumerAPI()
        self.consumer_group_api = ConsumerGroupAPI()
        self.repository_api = RepositoryAPI()
        self.service_api = ServiceAPI()
        self.file_api = FileAPI()
        self.package_api = PackageAPI()

# package actions -------------------------------------------------------------

class Info(PackageAction):

    name = "info"
    description = _('lookup information for a package')

    def setup_parser(self):
        self.parser.add_option("-n", "--name", dest="name",
                               help=_("package name to lookup (required)"))
        self.parser.add_option("--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        name = self.get_required_option('name')
        repoid = self.get_required_option('repoid')
        pkg = self.repository_api.get_package(repoid, name)
        if not pkg:
            utils.system_exit(os.EX_DATAERR,
                        _("Package [%s] not found in repo [%s]") %
                        (name, repoid))
        print_header(_("Package Information"))
        for p in pkg:
            print PACKAGE_INFO % (p['id'], p['name'], p['description'], p['arch'],
                                  p['version'], p['release'], p['epoch'], p['checksum'],
                                  p['filename'], p['size'], p['repo_defined'], p['download_url'],
                                  p['buildhost'], p['group'], p['license'], p['vendor'],
                                  p['provides'], p['requires'])
            print "\n"

class Install(PackageAction):

    name = "install"
    description = _('schedule a package install')

    def setup_parser(self):
        self.parser.add_option("-n", "--name", action="append", dest="pnames",
                               help=_("packages to be installed; to specify multiple packages use multiple -n"))
        id_group = OptionGroup(self.parser,
                               _('Consumer or Consumer Group id (one is required'))
        id_group.add_option("--consumerid", dest="consumerid",
                            help=_("consumer id"))
        id_group.add_option("--consumergroupid", dest="consumergroupid",
                            help=_("consumer group id"))
        self.parser.add_option_group(id_group)
        self.parser.add_option("--when", dest="when", default=None,
                               help=_("specifies when to execute the install.  "
                               "Format: iso8601, YYYY-MM-DDThh:mm"))
        self.parser.add_option("--nowait", dest="nowait", default=False,
            action="store_true",
            help=_("if specified, don't wait for the package install to finish, "
            "return immediately."))

    def run(self):
        consumerid = self.opts.consumerid
        consumergroupid = self.opts.consumergroupid
        if not (consumerid or consumergroupid):
            utils.system_exit(os.EX_USAGE,
                        _("Consumer or consumer group id required. try --help"))
        pnames = self.opts.pnames
        if not pnames:
            utils.system_exit(os.EX_DATAERR, _("Specify an package name to perform install"))
        if consumergroupid:
            self.on_group(consumergroupid, pnames)
        else:
            self.on_consumer(consumerid, pnames)

    def on_consumer(self, id, pnames):
        when = parse_at_schedule(self.opts.when)
        wait = self.getwait([id,])
        task = self.consumer_api.installpackages(id, pnames, when=when)
        print _('Created task id: %s') % task['id']
        print _('Task is scheduled for: %s') % when
        if not wait:
            utils.system_exit(0)
        state = None
        status = None
        spath = task['status_path']
        waitinit()
        while state not in ('finished', 'error', 'canceled', 'timed_out'):
            printwait()
            status = self.consumer_api.task_status(spath)
            state = status['state']
        if state == 'finished':
            print _('\n[%s] installed on %s') % \
                    (status['result'], (consumerid or consumergroupid))
        else:
            msg = _('\nPackage install failed: %s') % state
            if status is not None and state == 'error':
                msg += _('\nException: %s\nTraceback: %s') % \
                        (status['exception'], status['traceback'])
            utils.system_exit(-1, msg)

    def on_group(self, id, pnames):
        japi = JobAPI()
        when = parse_at_schedule(self.opts.when)
        group = self.consumer_group_api.consumergroup(id)
        if not group:
            system_exit(-1,
                _('Invalid group: %s' % id))
        wait = self.getwait(group['consumerids'])
        job = self.consumer_group_api.installpackages(id, pnames, when=when)
        print _('Created job id: %s') % job['id']
        print _('Job is scheduled for: %s') % when
        waitinit()
        while not job_end(job):
            job = japi.info(job['id'])
            printwait()
        print _('\nInstall Summary:')
        for t in job['tasks']:
            state = t['state']
            exception = t['exception']
            id, packages = t['args']
            print _('\t[ %-8s ] %s' % (state.upper(), id))
            if exception:
                print '\t\t, %s' % exception

    def getunavailable(self, ids):
        lst = []
        stats = self.service_api.agentstatus(ids)
        for id in ids:
            stat = stats[id]
            if stat[0]:
                continue
            lst.append(id)
        return lst

    def printunavailable(self, ualist):
        if ualist:
            sys.stdout.write(UNAVAILABLE)
            for id in ualist:
                print id

    def getwait(self, ids):
        wait = not self.opts.nowait
        ualist = self.getunavailable(ids)
        if ualist:
            self.printunavailable(ualist)
            if not askcontinue():
                utils.system_exit(0)
            # The consumer is unavailable, if wait was specified, verify that
            # we still want to wait.
            if wait:
                wait = askwait()
        return wait


class Search(PackageAction):

    name = "search"
    description = _('search for packages')

    def setup_parser(self):
        self.parser.add_option("-a", "--arch", dest="arch", default=None,
                               help=_("package arch regex to search for"))
        self.parser.add_option("-e", "--epoch", dest="epoch", default=None,
                               help=_("package epoch regex to search for"))
        self.parser.add_option("-f", "--filename", dest="filename", default=None,
                               help=_("package filename regex to search for"))
        self.parser.add_option("-n", "--name", dest="name", default=None,
                               help=_("package name regex to search for"))
        self.parser.add_option("-r", "--release", dest="release", default=None,
                               help=_("package release regex to search for"))
        self.parser.add_option("-v", "--version", dest="version", default=None,
                               help=_("package version regex to search for"))

    def run(self):
        arch = self.opts.arch
        epoch = self.opts.epoch
        filename = self.opts.filename
        name = self.opts.name
        release = self.opts.release
        version = self.opts.version
        pkgs = self.service_api.search_packages(name=name, epoch=epoch, version=version,
                release=release, arch=arch, filename=filename)
        if not pkgs:
            utils.system_exit(os.EX_DATAERR, _("No packages found."))

        name_field_size = self.get_field_size(pkgs, field_name="name")
        evra_field_size = self.get_field_size(pkgs, msg="%s:%s-%s.%s",
                field_names=("epoch", "version", "release", "arch"))
        filename_field_size = self.get_field_size(pkgs, field_name="filename")
        repos_field_size = self.get_field_size(pkgs, field_name="repos")
        print_header(_("Package Information"))
        print _("%s\t%s\t%s\t%s" % (self.form_item_string("Name", name_field_size),
                self.form_item_string("EVRA", evra_field_size),
                self.form_item_string("Filename", filename_field_size),
                self.form_item_string("Repositories", repos_field_size)))
        for pkg in pkgs:
            repos = ", ".join(pkg["repos"])
            print "%s\t%s\t%s\t%s" % \
                    (self.form_item_string(pkg["name"], name_field_size),
                    self.form_item_string("%s:%s-%s.%s" % (pkg["epoch"], pkg["version"],
                        pkg["release"], pkg["arch"]), evra_field_size),
                    self.form_item_string(pkg["filename"], filename_field_size),
                    repos)

    def form_item_string(self, msg, field_size):
        return string.ljust(msg, field_size)

    def get_field_size(self, items, msg=None, field_name="", field_names=()):
        largest_item_length = 0
        for item in items:
            if msg:
                test_string = msg % (field_names)
            else:
                test_string = "%s" % (item[field_name])
            if len(test_string) > largest_item_length:
                largest_item_length = len(test_string)
        return largest_item_length

class DependencyList(PackageAction):

    name = "deplist"
    description = _('List available dependencies')

    def setup_parser(self):
        self.parser.add_option("-n", "--name", action="append", dest="pnames", default=[],
                               help=_("package to lookup dependencies; to specify multiple packages use multiple -n"))
        self.parser.add_option("-r", "--repoid", action="append", dest="repoid", default=[],
                               help=_("repository labels; to specify multiple packages use multiple -r"))


    def run(self):

        if not self.opts.pnames:
            utils.system_exit(os.EX_DATAERR, \
                        _("package name is required to lookup dependencies."))
        repoid = [ r for r in self.opts.repoid or [] if len(r)]

        if not self.opts.repoid or not repoid:
            utils.system_exit(os.EX_DATAERR, \
                        _("At least one repoid is required to lookup dependencies."))

        pnames = self.opts.pnames

        repos = []
        for rid in repoid:
            repo = self.repository_api.repository(rid)
            if repo is None:
                print(_("Repository with id: [%s] not found. skipping" % rid))
                continue
            repos.append(rid)
        if not repos:
            utils.system_exit(os.EX_DATAERR)
        deps = self.service_api.dependencies(pnames, repos)
        if not deps['printable_dependency_result']:
            utils.system_exit(os.EX_OK, _("No dependencies available for Package(s) %s in repo %s") %
                        (pnames, repos))
        print_header(_("Dependencies for package(s) [%s]" % pnames))

        print deps['printable_dependency_result']
        print_header(_("Suggested Packages in Repo [%s]" % repos))
        if not deps['resolved']:
            utils.system_exit(os.EX_OK, _("None"))
        for dep, pkgs in deps['resolved'].items():
            for pkg in pkgs:
                print str(pkg['filename'])

# package command -------------------------------------------------------------

class Package(Command):

    name = "package"
    description = _('package specific actions to pulp server')

    actions = [ Info,
                Install,
                Search,
                DependencyList ]

# package plugin -------------------------------------------------------------

class PackagePlugin(AdminPlugin):

    commands = [ Package ]
