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


import base64
import os
import string
import sys
import time
from gettext import gettext as _
from optparse import OptionGroup

from pulp.client import utils
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.consumergroup import ConsumerGroupAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.api.upload import UploadAPI
from pulp.client.api.file import FileAPI
from pulp.client.api.package import PackageAPI
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit
from pulp.client.logutil import getLogger

log = getLogger(__name__)

# package action base class ---------------------------------------------------

class PackageAction(Action):

    def __init__(self):
        super(PackageAction, self).__init__()
        self.consumer_api = ConsumerAPI()
        self.consumer_group_api = ConsumerGroupAPI()
        self.repository_api = RepositoryAPI()
        self.service_api = ServiceAPI()
        self.file_api = FileAPI()
        self.package_api = PackageAPI()

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
        pkg = self.repository_api.get_package(repoid, name)
        if not pkg:
            system_exit(os.EX_DATAERR,
                        _("Package [%s] not found in repo [%s]") %
                        (name, repoid))
        print_header(_("Package Information"))
        #for key, value in pkg.items():
        #    print """%s:                \t%-25s""" % (key, value)
        for p in pkg:
            print """%s:                \t%-25s""" % (p['id'], p)


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
        self.add_scheduled_time_option()

    def run(self):
        consumerid = self.opts.consumerid
        consumergroupid = self.opts.consumergroupid
        if not (consumerid or consumergroupid):
            system_exit(os.EX_USAGE,
                        _("Consumer or consumer group id required. try --help"))
        pnames = self.opts.pnames
        if not pnames:
            system_exit(os.EX_DATAERR, _("Specify an package name to perform install"))
        when = self.parse_scheduled_time_option()
        if consumergroupid:
            task = self.consumer_group_api.installpackages(consumergroupid, pnames, when=when)
        else:
            task = self.consumer_api.installpackages(consumerid, pnames, when=when)
        print _('Created task id: %s') % task['id']
        print _('Task is scheduled for: %s') % \
                time.strftime("%Y-%m-%d %H:%M", time.localtime(when))
        state = None
        spath = task['status_path']
        while state not in ('finished', 'error', 'canceled', 'timed_out'):
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(2)
            status = self.consumer_api.task_status(spath)
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
        pkgs = self.service_api.search_packages(name=name, epoch=epoch, version=version,
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
        self.parser.add_option("-n", "--name", action="append", dest="pnames", type="string",
                               help=_("package to lookup dependencies; to specify multiple packages use multiple -n"))
        self.parser.add_option("-r", "--repoid", action="append", dest="repoid", type="string",
                               help=_("repository labels; to specify multiple packages use multiple -r"))


    def run(self):

        if not self.opts.pnames:
            system_exit(os.EX_DATAERR, \
                        _("package name is required to lookup dependencies."))

        repoid = [ r for r in self.opts.repoid or [] if len(r)]
        if not self.opts.repoid or not repoid:
            system_exit(os.EX_DATAERR, \
                        _("Atleast one repoid is required to lookup dependencies."))
        pnames = self.opts.pnames

        repos = []
        for rid in repoid:
            repo = self.repository_api.repository(rid)
            if repo is None:
                print(_("Repository with id: [%s] not found. skipping" % rid))
                continue
            repos.append(rid)
        if not repos:
            system_exit(os.EX_DATAERR)
        deps = self.service_api.dependencies(pnames, repos)
        if not deps['dependency_list']:
            system_exit(os.EX_OK, _("No dependencies available for Package(s) %s in repo %s") %
                        (pnames, repos))
        print_header(_("Dependencies for package(s) [%s]" % pnames))

        print deps['dependency_list']
        print_header(_("Suggested Packages in Repo [%s]" % repos))
        if not deps['available_packages']:
            system_exit(os.EX_OK, _("None"))
        for pkg in deps['available_packages']:
            print str(pkg['filename'])

class Upload(PackageAction):

    description = _('upload package(s) to pulp server;')

    def setup_parser(self):
        self.parser.add_option("--dir", dest="dir",
                               help=_("process packages from this directory"))
        self.parser.add_option("-r", "--repoid", action="append", dest="repoids",
                               help=_("Optional repoid, to associate the uploaded package"))
        self.parser.add_option("--nosig", action="store_true", dest="nosig",
                               help=_("pushes unsigned packages"))
        self.parser.add_option("--chunksize", dest="chunk", default=10485760, type=int,
                               help=_("chunk size to use for uploads. Default:10485760"))
        self.parser.add_option("-v", "--verbose", action="store_true", dest="verbose", help=_("verbose output."))

    def run(self):
        files = self.args
        repoids = [ r for r in self.opts.repoids or [] if len(r)]
        dir = self.opts.dir
        if dir:
            try:
                files += utils.processDirectory(dir)
            except Exception, e:
                system_exit(os.EX_DATAERR, _(str(e)))
        if not files:
            system_exit(os.EX_USAGE,
                        _("Error: Need to provide at least one file to perform upload"))
        if not self.opts.verbose:
            print _("* Starting Package Upload operation. See /var/log/pulp/client.log for more verbose output\n")
        else:
            print _("* Starting Package Upload\n")
        print _('* Performing Package Uploads to Pulp server')
        pids = {}
        fids = {}
        uapi = UploadAPI()
        for f in files:
            try:
                pkginfo = utils.processFile(f)
            except utils.FileError, e:
                msg = _('Error: %s') % e
                log.error(msg)
                if self.opts.verbose:
                    print msg
                continue

            if pkginfo.has_key('nvrea'):
                if not utils.is_signed(f) and not self.opts.nosig:
                    msg = _("Package [%s] is not signed. Please use --nosig. Skipping " % f)
                    log.error(msg)
                    if self.opts.verbose:
                        print msg
                    continue
                pkgobj = self.service_api.search_packages(filename=os.path.basename(f))
            else:
                pkgobj = self.service_api.search_file(pkginfo['pkgname'],
                                                   pkginfo['hashtype'],
                                                   pkginfo['checksum'])
            existing_pkg_checksums = []
            if pkgobj:
                existing_pkg_checksums = [pobj['checksum']['sha256'] for pobj in pkgobj]

            if pkginfo['checksum'] in existing_pkg_checksums:
                msg = _("Package [%s] already exists on the server with checksum [%s]") % \
                            (pobj['filename'], pobj['checksum']['sha256'])
                log.info(msg)
                if self.opts.verbose:
                    print msg
                if pkginfo['type'] == 'rpm':
                    pids[f] = pobj['id']
                else:
                    fids[f] = pobj['id']
                continue
            upload_id = uapi.upload(f, chunksize=self.opts.chunk)
            uploaded = uapi.import_content(pkginfo, upload_id)
            if uploaded:
                if pkginfo['type'] == 'rpm':
                    pids[f] = uploaded['id']
                else:
                    fids[f] = uploaded['id']
                msg = _("Successfully uploaded [%s] to server") % pkginfo['pkgname']
                log.info(msg)
                if self.opts.verbose:
                    print msg
            else:
                msg = _("Error: Failed to upload [%s] to server") % pkginfo['pkgname']
                log.error(msg)
                if self.opts.verbose:
                    print msg
        if not repoids:
            system_exit(os.EX_OK, _("\n* Content Upload complete."))
        if not pids and not fids:
            system_exit(os.EX_DATAERR, _("No applicable content to associate."))
        print _('\n* Performing Repo Associations ')
        # performing package Repo Association
        for rid in repoids:
            repo = self.repository_api.repository(rid)
            if not repo:
                msg = _("Error: Repo %s does not exist; skipping") % rid
                log.error(msg)
                if self.opts.verbose:
                    print msg
                continue
            if len(pids):
                self.repository_api.add_package(rid, pids.values())

            if len(fids):
                self.repository_api.add_file(rid, fids.values())
            msg = _('Successfully associated the following to Repo [%s]: \n Packages: \n%s \n \n Files: \n%s' % \
                    (rid, '\n'.join(pids.keys()) or None, '\n'.join(fids.keys()) or None))
            log.info(msg)
            if self.opts.verbose:
                print msg
        print _("\n* Package Upload complete.")


class List(PackageAction):

    description = _('list package(s) on pulp server;')

    def setup_parser(self):
        self.parser.add_option("--orphaned", action="store_true", dest="orphaned",
                               help=_("list of orphaned packages"))
        self.parser.add_option("--repoid", dest="repoid",
                               help=_("list packages in specified repo"))

    def run(self):
        if not self.opts.orphaned and not self.opts.repoid:
            system_exit(os.EX_USAGE, "--orphaned or --repoid is required to list packages")

        if self.opts.orphaned:
            orphaned_pkgs = self.package_api.orphaned_packages()

            for pkg in orphaned_pkgs:
                try:
                    print "%s,%s" % (pkg['filename'], pkg['checksum']['sha256'])
                except:
                    pass
        if self.opts.repoid:
            repo_pkgs = self.repository_api.packages(self.opts.repoid)
            for pkg in repo_pkgs:
                try:
                    print "%s,%s" % (pkg['filename'], pkg['checksum']['sha256'])
                except:
                    pass

# package command -------------------------------------------------------------

class Package(Command):

    description = _('package specific actions to pulp server')
