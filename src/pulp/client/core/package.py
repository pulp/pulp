#!/usr/bin/python
#
# Pulp Registration and subscription module
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import os
import string
import sys
import time
from gettext import gettext as _
from optparse import OptionGroup

from pulp.client.connection import RepoConnection, ConsumerConnection, ConsumerGroupConnection, SearchConnection
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit

# package action base class ---------------------------------------------------

class PackageAction(Action):

    def setup_connections(self):

        self.sconn = SearchConnection()
        self.rconn = RepoConnection()
        self.cconn = ConsumerConnection()
        self.cgconn = ConsumerGroupConnection()

# package actions -------------------------------------------------------------

class Info(PackageAction):

    description = _('lookup information for a package')

    def setup_parser(self):
        self.parser.add_option("-n", "--name", dest="name",
                               help=_("package name to lookup (required)"))
        self.parser.add_option("--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        name = self.get_required_option('name')
        repoid = self.get_required_option('repoid')
        pkg = self.rconn.get_package(repoid, name)
        if not pkg:
            system_exit(os.EX_DATAERR,
                        _("Package [%s] not found in repo [%s]") %
                        (name, repoid))
        print_header(_("Package Information"))
        for key, value in pkg.items():
            print """%s:                \t%-25s""" % (key, value)


class Install(PackageAction):

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

    def run(self):
        consumerid = self.opts.consumerid
        consumergroupid = self.opts.consumergroupid
        if not (consumerid or consumergroupid):
            system_exit(os.EX_USAGE,
                        _("Consumer or consumer group id required. try --help"))
        pnames = self.opts.pnames
        if not pnames:
            system_exit(os.EX_DATAERR, _("Nothing to upload."))
        if consumergroupid:
            task = self.cgconn.installpackages(consumergroupid, pnames)
        else:
            task = self.cconn.installpackages(consumerid, pnames)
        print _('Created task id: %s') % task['id']
        state = None
        spath = task['status_path']
        while state not in ('finished', 'error', 'canceled', 'timed_out'):
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(2)
            status = self.cconn.task_status(spath)
            state = status['state']
        if state == 'finished':
            print _('\n[%s] installed on %s') % \
                  (status['result'], (consumerid or consumergroupid))
        else:
            system_exit(-1, _("\nPackage install failed"))

class Search(PackageAction):

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
        pkgs = self.sconn.packages(name=name, epoch=epoch, version=version,
                release=release, arch=arch, filename=filename)
        if not pkgs:
           system_exit(os.EX_DATAERR, _("No packages found."))

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

    description = _('List available dependencies')
    
    def setup_parser(self):
        self.parser.add_option("-n", "--name", action="append", dest="pnames",
                               help=_("packages to lookup dependencies; to specify multiple packages use multiple -n"))
        self.parser.add_option("--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        pnames = self.opts.pnames
        if not pnames:
            system_exit(os.EX_DATAERR, \
                        _("Atleast one package needs to be specified to lookup dependencies."))
        repoid = self.get_required_option('repoid')
        deps = self.rconn.get_package_dependency(repoid, pnames)
        if not deps['dependency_list']:
            system_exit(os.EX_OK, _("No dependencies available for Package(s) [%s] in repo [%s]") %
                        (pnames, repoid))
        print_header(_("Dependencies for package(s) [%s]" % pnames))
#        for dep in deps['dependency_list']:
#            print str(dep)
        print deps['dependency_list']
        print_header(_("Available Packages satisfying the dependencies in Repo [%s]" % repoid))
        if not deps['available_packages']:
            system_exit(os.EX_OK, _("None"))
        for pkg in deps['available_packages']:
            print str(pkg['filename'])
            
# package command -------------------------------------------------------------

class Package(Command):

    description = _('package specific actions to pulp server')
