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
import sys
from gettext import gettext as _

from pulp.client import utils
from pulp.client.api.repository import RepositoryAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.api.upload import UploadAPI
from pulp.client.api.file import FileAPI
from pulp.client.api.package import PackageAPI
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import system_exit
from pulp.client.logutil import getLogger

log = getLogger(__name__)

# package action base class ---------------------------------------------------

class ContentAction(Action):

    def __init__(self):
        super(ContentAction, self).__init__()
        self.repository_api = RepositoryAPI()
        self.service_api = ServiceAPI()
        self.file_api = FileAPI()
        self.package_api = PackageAPI()

class Upload(ContentAction):

    description = _('upload content to pulp server;')

    def setup_parser(self):
        self.parser.add_option("--dir", dest="dir",
                               help=_("process content from this directory"))
        self.parser.add_option("-r", "--repoid", action="append", dest="repoids",
                               help=_("Optional repoid, to associate the uploaded content"))
        self.parser.add_option("--nosig", action="store_true", dest="nosig",
                               help=_("pushes unsigned content(rpms)"))
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
        exit_code = 0
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
                    exit_code = os.EX_DATAERR
                    continue
                pkgobj = self.service_api.search_packages(filename=os.path.basename(f))
            else:
                pkgobj = self.service_api.search_file(pkginfo['pkgname'],
                                                   pkginfo['hashtype'],
                                                   pkginfo['checksum'])
            existing_pkg_checksums = {}
            if pkgobj:
                for pobj in pkgobj:
                    existing_pkg_checksums[pobj['checksum']['sha256']] = pobj

            if pkginfo['checksum'] in existing_pkg_checksums.keys():
                pobj = existing_pkg_checksums[pkginfo['checksum']]
                msg = _("Package [%s] already exists on the server with checksum [%s]") % \
                            (pobj['filename'], pobj['checksum']['sha256'])
                log.info(msg)
                if self.opts.verbose:
                    print msg
                if pkginfo['type'] == 'rpm':
                    pids[os.path.basename(f)] = pobj['id']
                else:
                    fids[os.path.basename(f)] = pobj['id']
                continue
            upload_id = uapi.upload(f, chunksize=self.opts.chunk)
            uploaded = uapi.import_content(pkginfo, upload_id)
            if uploaded:
                if pkginfo['type'] == 'rpm':
                    pids[os.path.basename(f)] = uploaded['id']
                else:
                    fids[os.path.basename(f)] = uploaded['id']
                msg = _("Successfully uploaded [%s] to server") % pkginfo['pkgname']
                log.info(msg)
                if self.opts.verbose:
                    print msg
            else:
                msg = _("Error: Failed to upload [%s] to server") % pkginfo['pkgname']
                log.error(msg)
                if self.opts.verbose:
                    print msg
                exit_code = os.EX_DATAERR
        if not repoids:
            system_exit(exit_code, _("\n* Content Upload complete."))
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
            msg = _('Package association Complete for Repo [%s]: \n Packages: \n%s \n \n Files: \n%s' % \
                    (rid, '\n'.join(pids.keys()) or None, '\n'.join(fids.keys()) or None))
            log.info(msg)
            if self.opts.verbose:
                print msg
        system_exit(exit_code, _("\n* Content Upload complete."))


class List(ContentAction):

    description = _('list content(packages/files) on pulp server;')

    def setup_parser(self):
        self.parser.add_option("--orphaned", action="store_true", dest="orphaned",
                               help=_("list of orphaned content"))
        self.parser.add_option("--repoid", dest="repoid",
                               help=_("list content in specified repo"))

    def run(self):
        if not self.opts.orphaned and not self.opts.repoid:
            system_exit(os.EX_USAGE, "--orphaned or --repoid is required to list packages")

        if self.opts.orphaned:
            orphaned_pkgs = self.package_api.orphaned_packages()
            orphaned_files = self.file_api.orphaned_files()
            orphaned = orphaned_pkgs + orphaned_files
            if not len(orphaned):
                system_exit(os.EX_OK, _("No orphaned content on server"))
            for pkg in orphaned:
                try:
                    print "%s,%s" % (pkg['filename'], pkg['checksum']['sha256'])
                except:
                    pass
        if self.opts.repoid:
            repo_pkgs = self.repository_api.packages(self.opts.repoid)
            repo_files = self.repository_api.list_files(self.opts.repoid)
            repo_data = repo_pkgs + repo_files
            if not len(repo_data):
                system_exit(os.EX_OK, _("No content in the repo [%s]" % self.opts.repoid))
            for pkg in repo_data:
                try:
                    print "%s,%s" % (pkg['filename'], pkg['checksum']['sha256'])
                except:
                    pass

# content command -------------------------------------------------------------

class Content(Command):

    description = _('generic content specific actions to pulp server')

