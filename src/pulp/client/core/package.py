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
import base64
from gettext import gettext as _
from optparse import OptionGroup
from pulp.client import utils
from pulp.client.connection import RepoConnection, ConsumerConnection, \
                                   ConsumerGroupConnection, ServicesConnection
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit
from pulp.client.credentials import CredentialError
from pulp.client.logutil import getLogger

log = getLogger(__name__)

# package command errors ---------------------------------------------------------
class FileError(Exception):
    pass

# package action base class ---------------------------------------------------

class PackageAction(Action):

    def setup_connections(self):
        try:
            self.rconn = RepoConnection()
            self.cconn = ConsumerConnection()
            self.cgconn = ConsumerGroupConnection()
            self.sconn = ServicesConnection()
        except CredentialError, ce:
            system_exit(-1, str(ce))

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
            task = self.cgconn.installpackages(consumergroupid, pnames, when=when)
        else:
            task = self.cconn.installpackages(consumerid, pnames, when=when)
        print _('Created task id: %s') % task['id']
        print _('Task is scheduled for: %s') % \
                time.strftime("%Y-%m-%d %H:%M", time.localtime(when))
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
        pkgs = self.sconn.search_packages(name=name, epoch=epoch, version=version,
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
            repo = self.rconn.repository(rid)
            if repo is None:
                print(_("Repository with id: [%s] not found. skipping" % rid))
                continue
            repos.append(rid)
        if not repos:
            system_exit(os.EX_DATAERR)
        deps = self.sconn.dependencies(pnames, repos)
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
        self.parser.add_option("-v", "--verbose", action="store_true", dest="verbose", help=_("verbose output."))

    def run(self):
        files = self.args
        repoids = [ r for r in self.opts.repoids or [] if len(r)]
        dir = self.opts.dir
        if dir:
            try:
                files += utils.processDirectory(dir, "rpm")
            except Exception, e:
                system_exit(os.EX_DATAERR, _(str(e)))
        if not files:
            system_exit(os.EX_USAGE,
                        _("Need to provide at least one file to perform upload"))
        if not self.opts.verbose:
            print _("* Starting Package Upload operation. See /var/log/pulp/client.log for more verbose output")
        else:
            print _("* Starting Package Upload\n")
        print _('* Performing Package Uploads to Pulp server')
        pids = {}
        for frpm in files:
            pkgobj = self.sconn.search_packages(filename=os.path.basename(frpm))
            if pkgobj:
                pkgobj = pkgobj[0]
                msg = _("Package [%s] already exists on the server with checksum [%s]") % \
                            (pkgobj['filename'], pkgobj['checksum'])
                log.info(msg)
                if self.opts.verbose:
                    print msg
                pids[frpm] = pkgobj['id']
                continue
            try:
                pkginfo = utils.processRPM(frpm)
            except FileError, e:
                print >> sys.stderr, _('error: %s') % e
                continue
            if not pkginfo.has_key('nvrea'):
                msg = _("Package %s is not an rpm; skipping") % frpm
                log.error(msg)
                if self.opts.verbose:
                    print msg
                continue
            name, version, release, epoch, arch = pkginfo['nvrea']
            nvrea = [{'name' : name,
                     'version' : version,
                     'release' : release, 
                     'epoch'   : epoch,
                     'arch'    : arch}]

            pkgstream = base64.b64encode(open(frpm).read())
            uploaded = self.sconn.upload(pkginfo, pkgstream)
            if uploaded:
                pids[frpm] = uploaded['id']
                msg = _("Successfully uploaded [%s] to server") % pkginfo['pkgname']
                log.info(msg)
                if self.opts.verbose:
                    print msg
            else:
                msg = _("Failed to upload [%s] to server") % pkginfo['pkgname']
                log.error(msg)
                if self.opts.verbose:
                    print msg
        if not repoids or not pids:
            system_exit(os.EX_OK)
        print _('\n* Performing Repo Associations: ')
        # performing package Repo Association
        for rid in repoids:
            repo = self.rconn.repository(rid)
            if not repo:
                msg = _("Repo %s does not exist; skipping") % rid
                log.error(msg)
                if self.opts.verbose:
                    print msg
                continue
            self.rconn.add_package(rid, pids.values())
            msg =  _('Successfully associated following Packages to Repo [%s]: \n%s' % (rid, '\n'.join(pids.keys())))
            log.info(msg)
            if self.opts.verbose:
                print msg
        print _("\n* Package Upload complete.")


            
# package command -------------------------------------------------------------

class Package(Command):

    description = _('package specific actions to pulp server')
