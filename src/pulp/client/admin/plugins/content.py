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

import os
import sys
from gettext import gettext as _

from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api.file import FileAPI
from pulp.client.api.package import PackageAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.api.upload import UploadAPI
from pulp.client.lib import utils
from pulp.client.lib.logutil import getLogger
from pulp.client.pluginlib.command import Action, Command

from rpm import _rpm

log = getLogger(__name__)

# package action base class ---------------------------------------------------

class ContentAction(Action):

    def __init__(self, cfg):
        super(ContentAction, self).__init__(cfg)
        self.repository_api = RepositoryAPI()
        self.service_api = ServiceAPI()
        self.file_api = FileAPI()
        self.package_api = PackageAPI()

class Upload(ContentAction):

    name = "upload"
    description = _('upload content to the Pulp server')

    def setup_parser(self):
        self.parser.add_option("--dir", dest="dir",
                               help=_("process content from this directory"))
        self.parser.add_option("-r", "--repoid", action="append", dest="repoids",
                               help=_("repoid to associate the uploaded content"))
        self.parser.add_option("--nosig", action="store_true", dest="nosig",
                               help=_("pushes unsigned content(rpms)"))
        self.parser.add_option("--chunksize", dest="chunk", default=10485760, type=int,
                               help=_("chunk size to use for uploads; Default:10485760"))
        self.parser.add_option("-v", "--verbose", action="store_true", dest="verbose", help=_("verbose output."))

    def run(self):
        files = self.args
        repoids = [ r for r in self.opts.repoids or [] if len(r)]
        dir = self.opts.dir
        if dir:
            try:
                files += utils.processDirectory(dir)
            except Exception, e:
                utils.system_exit(os.EX_DATAERR, _(str(e)))
        if not files:
            utils.system_exit(os.EX_USAGE,
                        _("Error: Need to provide at least one file to perform upload"))
        if not self.opts.verbose:
            print _("* Starting Content Upload operation. See /var/log/pulp/client.log for more verbose output\n")
        else:
            print _("* Starting Content Upload\n")
        print _('* Performing Content Uploads to Pulp server')
        pids = {}
        fids = {}
        exit_code = 0
        uapi = UploadAPI()
        for f in files:
            try:
                if not self.opts.nosig and f.endswith(".rpm") and not utils.is_signed(f):
                    msg = _("Package [%s] is not signed. Please use --nosig. Skipping " % f)
                    log.error(msg)
                    if self.opts.verbose:
                        print msg
                    exit_code = os.EX_DATAERR
                    continue
            except _rpm.error:
                log.error("Could not read the header, perhaps not an rpm; continue")
            except Exception,e:
                msg = "Error: %s" % e
                log.error(msg)
                exit_code = os.EX_DATAERR
                if self.opts.verbose:
                    print msg
                continue
            try:
                metadata = utils.processFile(f)
            except utils.FileError, e:
                msg = _('Error: %s') % e
                log.error(msg)
                if self.opts.verbose:
                    print msg
                continue
            if metadata.has_key('nvrea'):
                pkgobj = self.service_api.search_packages(filename=os.path.basename(f), regex=False)
            else:
                pkgobj = self.service_api.search_file(metadata['pkgname'],
                                                   metadata['hashtype'],
                                                   metadata['checksum'])
            existing_pkg_checksums = {}
            if pkgobj:
                for pobj in pkgobj:
                    existing_pkg_checksums[pobj['checksum'][pobj['checksum'].keys()[0]]] = pobj

            if metadata['checksum'] in existing_pkg_checksums.keys():
                pobj = existing_pkg_checksums[metadata['checksum']]
                msg = _("Content [%s] already exists on the server with checksum [%s]") % \
                            (pobj['filename'], pobj['checksum'][pobj['checksum'].keys()[0]])
                log.info(msg)
                if self.opts.verbose:
                    print msg
                if metadata['type'] == 'rpm':
                    pids[os.path.basename(f)] = pobj['id']
                else:
                    fids[os.path.basename(f)] = pobj['id']
                continue
            upload_id = uapi.upload(f, checksum=metadata['checksum'], chunksize=self.opts.chunk)
            uploaded = uapi.import_content(metadata, upload_id)
            if uploaded:
                if metadata['type'] == 'rpm':
                    pids[os.path.basename(f)] = uploaded['id']
                else:
                    fids[os.path.basename(f)] = uploaded['id']
                msg = _("Successfully uploaded [%s] to server") % metadata['pkgname']
                log.info(msg)
                if self.opts.verbose:
                    print msg
            else:
                msg = _("Error: Failed to upload [%s] to server") % metadata['pkgname']
                log.error(msg)
                if self.opts.verbose:
                    print msg
                exit_code = os.EX_DATAERR
        if not repoids:
            utils.system_exit(exit_code, _("\n* Content Upload complete."))
        if not pids and not fids:
            utils.system_exit(os.EX_DATAERR, _("No applicable content to associate."))
        print _('\n* Performing Repo Associations ')
        filtered_count = 0
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
                errors, filtered_count = self.repository_api.add_package(rid, pids.values())
                for e in errors:
                    error_message = e[4]
                    if error_message:
                        exit_code = os.EX_DATAERR
                        print "%s" % (error_message)
                print _("Packages skipped because of filters associated with the repository %s : %s" % (rid, filtered_count))
                if filtered_count < len(pids):
                    task = self.repository_api.generate_metadata(rid)
                    print _("\n* Metadata generation has been scheduled for repository [%s] with a task id [%s]; use `pulp-admin repo generate_metadata --status` to check the status." % (rid, task['id']))

            if len(fids):
                self.repository_api.add_file(rid, fids.values())
            if not filtered_count:
                msg = _('\nContent association Complete for Repo [%s]: \n Packages: \n%s \n \n Files: \n%s' % \
                        (rid, '\n'.join(pids.keys()) or None, '\n'.join(fids.keys()) or None))
            else:
                msg = _('Content association Complete for Repo [%s]' % rid)
            log.info(msg)
            if self.opts.verbose:
                print msg
        utils.system_exit(exit_code, _("\n* Content Upload complete."))


class List(ContentAction):

    name = "list"
    description = _('list content(packages/files) on the Pulp server')

    def setup_parser(self):
        self.parser.add_option("--orphaned", action="store_true", dest="orphaned",
                               help=_("list only orphaned content"))
        self.parser.add_option("--repoid", dest="repoid",
                               help=_("list content from a specific repo"))

    def run(self):
        if not self.opts.orphaned and not self.opts.repoid:
            utils.system_exit(os.EX_USAGE, "--orphaned or --repoid is required to list packages")
        if self.opts.orphaned:
            orphaned_pkgs = self.package_api.orphaned_packages()
            orphaned_files = self.file_api.orphaned_files()
            orphaned = orphaned_pkgs + orphaned_files
            if not len(orphaned):
                utils.system_exit(os.EX_OK, _("No orphaned content on server"))
            for pkg in orphaned:
                for checksum in pkg['checksum'].values():
                    print "%s,%s" % (pkg['filename'], checksum)
        if self.opts.repoid:
            repo_pkgs = self.repository_api.packages(self.opts.repoid) or []
            repo_files = self.repository_api.list_files(self.opts.repoid) or []
            repo_data = repo_pkgs + repo_files
            if not len(repo_data):
                utils.system_exit(os.EX_OK, _("No content in the repo [%s]" % self.opts.repoid))
            for pkg in repo_data:
                for checksum in pkg['checksum'].values():
                    print "%s,%s" % (pkg['filename'], checksum)


class Delete(ContentAction):
    
    name = "delete"
    description = _("delete content from the Pulp server")

    def setup_parser(self):
        self.parser.add_option("-f", "--filename", action="append", dest="files",
                               help=_("content filename to delete from server"))
        self.parser.add_option("--csv", dest="csv",
                               help=_("a content csv with list of files to remove;format:filename,checksum"))
        
    def run(self):
        if self.opts.files and self.opts.csv:
            utils.system_exit(os.EX_USAGE, _("Error: Both --files and --csv cannot be used in the same command."))
            
        fids = {}
        if self.opts.csv:
            if not os.path.exists(self.opts.csv):
                utils.system_exit(os.EX_DATAERR, _("CSV file [%s] not found" % self.opts.csv))
            flist = utils.parseCSV(self.opts.csv)
        else:
            if not self.opts.files:
                utils.system_exit(os.EX_USAGE, _("Error: Need to provide at least one file to perform remove."))
            flist = self.opts.files
        exit_code = 0    
        fids = {}
        for f in flist:
            if isinstance(f, list) or len(f) == 2:
                if not len(f) == 2:
                    log.error("Bad format [%s] in csv, skipping" % f)
                    continue
                filename, checksum = f
            else:
                filename, checksum = f, None
            #TODO: Once package/file api are merge to contentapi, replace this check with global content_search
            if filename.endswith('.rpm'):
                pkgobj = self.service_api.search_packages(filename=filename, checksum=checksum, regex=False)
            else:
                pkgobj = self.service_api.search_file(filename=filename, checksum=checksum)

            if not pkgobj:
                print _("Content with filename [%s] could not be found on server; skipping delete" % filename)
                exit_code = os.EX_DATAERR
                continue
            pobj = None
            if len(pkgobj) > 1:
                if not self.opts.csv:
                    print _("There is more than one file with filename [%s]. Please use csv option to include checksum. Skipping delete" % filename)
                    exit_code = os.EX_DATAERR
                    continue
                else:
                    for fo in pkgobj:
                        if fo['filename'] == filename and \
                           fo['checksum'][fo['checksum'].keys()[0]] == checksum:
                            pobj = fo
            else:
                pobj = pkgobj[0]
            
            if not pobj:
                print _("Content with filename [%s] could not be found on server; skipping delete" % filename)
                exit_code = os.EX_DATAERR
                continue
            if pobj.has_key('repoids') and len(pobj['repoids']):
                print _("Filename [%s] is currently associated with one or more repositories; skipping delete" % filename)
                exit_code = os.EX_DATAERR
                continue
            #TODO: Once package/file api are merge to contentapi, replace this check with global content_search
            if pobj['filename'].endswith('.rpm'):
                self.package_api.delete(pobj['id'])
            else:
                self.file_api.delete(pobj['id'])
            
            print _("Successfully deleted content [%s] from pulp server" % filename)
        utils.system_exit(exit_code)

# content command -------------------------------------------------------------

class Content(Command):

    name = "content"
    description = _('generic content specific actions to pulp server')

    actions = [ Upload,
                List,
                Delete ]

# content plugin -------------------------------------------------------------

class ContentPlugin(AdminPlugin):

    name = "content"
    commands = [ Content ]
