#!/usr/bin/python
#
# Pulp Repo management module
#
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
import gettext
import sys
import time

import pulp.client.constants as constants
import pulp.client.utils as utils
from pulp.client.config import Config
from pulp.client.connection import RepoConnection, RestlibException
from pulp.client.core.basecore import print_header, BaseCore, systemExit
from pulp.client.logutil import getLogger

# -----------------------------------------------------------------------------

CFG = Config()
log = getLogger(__name__)

_ = gettext.gettext

# repo command errors ---------------------------------------------------------

class FileError(Exception):
    pass

class SyncError(Exception):
    pass

# core repos class ------------------------------------------------------------

class repo(BaseCore):

    _default_actions = {"create": "Create a repo",
                        "update": "Update a repo",
                        "list": "List available repos",
                        "delete": "Delete a repo",
                        'status': 'Show the status of a repo',
                        "sync": "Sync data to this repo from the feed",
                        "cancel_sync": "Cancel a running sync",
                        "upload": "Upload package(s) to this repo",
                        "schedules": "List all repo schedules", }

    def __init__(self, actions=None):
        usage = "repo [OPTIONS]"
        shortdesc = "repository specifc actions to pulp server."
        desc = ""
        self.name = "repo"
        self.actions = actions or self._default_actions
        BaseCore.__init__(self, "repo", usage, shortdesc, desc)

    def load_server(self):
        self.pconn = RepoConnection(host=CFG.server.host or "localhost",
                                    port=CFG.server.port or 443,
                                    username=self.username,
                                    password=self.password,
                                    cert_file=self.cert_filename,
                                    key_file=self.key_filename)

    def _add_create_update_options(self):
            self.parser.add_option("--id", dest="id",
                           help="Repository Id")
            self.parser.add_option("--name", dest="name",
                                   help="Common repository name")
            self.parser.add_option("--arch", dest="arch",
                                   help="Package arch the repo should support.")
            self.parser.add_option("--feed", dest="feed",
                                   help="Url feed to populate the repo")
            self.parser.add_option("--cacert", dest="cacert",
                                   help="Path location to CA Certificate.")
            self.parser.add_option("--cert", dest="cert",
                                   help="Path location to Entitlement Certificate.")
            self.parser.add_option("--key", dest="key",
                                   help="Path location to Entitlement Cert Key.")
            self.parser.add_option("--schedule", dest="schedule",
                                   help="Schedule for automatically synchronizing the repository")
            self.parser.add_option("--symlinks", action="store_true", dest="symlinks",
                                   help="Use symlinks instead of copying bits locally.\
                                   Applicable for local syncs")
            self.parser.add_option("--relativepath", dest="relativepath",
                                   help="Relative path where the repo is stored and exposed to clients.\
                                   This defaults to feed path if not specified.")
            self.parser.add_option("--groupid", dest="groupid",
                                   help="A group to which the repo belongs.This is just a string identifier.")

    def generate_options(self):
        self.action = self._get_action()
        if self.action == "create":
            usage = "repo create [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self._add_create_update_options()
        if self.action == "update":
            usage = "repo update [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self._add_create_update_options()
        if self.action == "sync":
            usage = "repo sync [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id", help="Repository Id")
            self.parser.add_option("--timeout", dest="timeout", help="Sync Timeout")
            self.parser.add_option('-F', '--foreground', dest='foreground',
                                   action='store_true', default=False,
                                   help='Sync repo in the foreground')
        if self.action == 'status':
            usage = 'repo status [OPTIONS]'
            self.parser.add_option("--id", dest="id", help="Repository Id")

        if self.action == "cancel_sync":
            usage = "repo cancel_sync [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id", help="Repository Id")
            self.parser.add_option("--taskid", dest="taskid", help="Task ID")

        if self.action == "delete":
            usage = "repo delete [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id", help="Repository Id")

        if self.action == "list":
            usage = "repo list [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--groupid", action="append", dest="groupid",
                                  help="Filter repos by group id")

        if self.action == "upload":
            usage = "repo upload [OPTIONS] <package>"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id", help="Repository Id")
            self.parser.add_option("--dir", dest="dir",
                                  help="Process packages from this directory")

        if self.action == "schedules":
            usage = "repo schedules"
            self.setup_option_parser(usage, "", True)

    def _do_core(self):
        if self.action == "create":
            self._create()
        if self.action == "update":
            self._update()
        if self.action == "list":
            self._list()
        if self.action == 'status':
            self._status()
        if self.action == "sync":
            self._sync()
        if self.action == "cancel_sync":
            self._cancel_sync()
        if self.action == "delete":
            self._delete()
        if self.action == "upload":
            self._upload()
        if self.action == "schedules":
            self._schedules()

    def _get_cert_options(self):
        cert_data = None
        if self.options.cacert and self.options.cert and self.options.key:
            cert_data = {"ca": utils.readFile(self.options.cacert),
                         "cert": utils.readFile(self.options.cert),
                         "key": utils.readFile(self.options.key)}
        return cert_data

    def _create(self):
        if not self.options.id:
            print _("repo id required. Try --help")
            sys.exit(0)
        if not self.options.name:
            self.options.name = self.options.id
        if not self.options.arch:
            self.options.arch = "noarch"

        symlinks = self.options.symlinks or False

        relative_path = self.options.relativepath or None

        groupid = self.options.groupid or None

        cert_data = self._get_cert_options()
        try:
            repo = self.pconn.create(self.options.id, self.options.name,
                                     self.options.arch, self.options.feed,
                                     symlinks, self.options.schedule, cert_data=cert_data,
                                     relative_path=relative_path, groupid=groupid)
            print _(" Successfully created Repo [ %s ]") % repo['id']
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            systemExit(e.code, e.msg)

    def _update(self):
        if not self.options.id:
            print("repo id required. Try --help")
            sys.exit(1)
        try:
            repo = self.pconn.repository(self.options.id)
            if not repo:
                print("repo with id: [%s] not found." % self.options.id)
                sys.exit(1)
            optdict = vars(self.options)
            for field in optdict.keys():
                if (repo.has_key(field) and optdict[field]):
                    repo[field] = optdict[field]
            # Have to set this manually since the repo['feed'] is a 
            # complex sub-object inside the repo
            if self.options.feed:
                repo['feed'] = self.options.feed
            self.pconn.update(repo)
            print _(" Successfully updated Repo [ %s ]") % repo['id']
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _list(self):
        try:
            if self.options.groupid:
                repos = self.pconn.repositories_by_groupid(groups=self.options.groupid)
            else:
                repos = self.pconn.repositories()
            if not len(repos):
                print _("No repos available to list")
                sys.exit(0)
            print_header('List of Available Repositories')
            for repo in repos:
                print constants.AVAILABLE_REPOS_LIST % (
                    repo["id"], repo["name"], repo["source"], repo["arch"],
                    repo["sync_schedule"], repo['package_count'], repo['files_count'])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _status(self):
        if not self.options.id:
            print _("repo id required. Try --help")
            sys.exit(0)
        try:
            repo = self.pconn.repository(self.options.id)
            syncs = self.pconn.sync_list(self.options.id)
            print _('Repository: %s') % repo['id']
            print _('Number of Packages: %d') % repo['package_count']
            last_sync = 'never' if repo['last_sync'] is None else str(repo['last_sync'])
            print _('Last Sync: %s') % last_sync
            if syncs and syncs[0]['state'] in ('waiting', 'running'):
                print _('Currently Syncing:'),
                if syncs[0]['progress'] is None:
                    print _('starting')
                else:
                    pkgs_left = syncs[0]['progress']['items_left']
                    pkgs_total = syncs[0]['progress']['items_total']
                    bytes_left = float(syncs[0]['progress']['size_left'])
                    bytes_total = float(syncs[0]['progress']['size_total'])
                    percent = (bytes_total - bytes_left) / bytes_total
                    print '%d%% done (%d of %d packages downloaded)' % \
                        (int(percent), (pkgs_total - pkgs_left), pkgs_total)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)


    def _print_sync_progress(self, progress):
        # erase the previous progress
        if hasattr(self, '_previous_progress'):
            sys.stdout.write('\b' * (len(self._previous_progress)))
            sys.stdout.flush()
            delattr(self, '_previous_progress')
        # handle the initial None case
        if progress is None:
            self._previous_progress = '[' + ' ' * 53 + '] 0%'
            sys.stdout.write(self._previous_progress)
            sys.stdout.flush()
            return
        # calculate the progress
        done = float(progress['size_total']) - float(progress['size_left'])
        total = float(progress['size_total'])
        portion = done / total
        percent = str(int(100 * portion))
        pkgs_done = str(progress['items_total'] - progress['items_left'])
        pkgs_total = str(progress['items_total'])
        # create the progress bar
        bar_width = 50
        bar_ticks = '=' * int(bar_width * portion)
        bar_spaces = ' ' * (bar_width - len(bar_ticks))
        bar = '[' + bar_ticks + bar_spaces + ']'
        # set the previous progress and print
        self._previous_progress = '%s %s%% (%s of %s pkgs)' % \
            (bar, percent, pkgs_done, pkgs_total)
        sys.stdout.write(self._previous_progress)
        sys.stdout.flush()

    def _print_sync_finish(self, state, progress):
        self._print_sync_progress(progress)
        print ''
        print _('Sync: %s') % state.title()

    def _sync_foreground(self, task):
        print _('you can safely CTRL+C this current command and it will continue')
        try:
            while task['state'] not in ('finished', 'error', 'timed out', 'canceled'):
                self._print_sync_progress(task['progress'])
                time.sleep(0.25)
                task = self.pconn.sync_status(task['status_path'])
        except KeyboardInterrupt:
            print ''
            return
        self._print_sync_finish(task['state'], task['progress'])
        if task['state'] == 'error':
            raise SyncError(task['traceback'][-1])

    def _sync(self):
        if not self.options.id:
            print _("repo id required. Try --help")
            sys.exit(0)
        try:
            task = self.pconn.sync(self.options.id, self.options.timeout)
            print _('Sync for repo %s started') % self.options.id
            if self.options.foreground:
                self._sync_foreground(task)
            else:
                print _('Use "repo status" to check on the progress')
        except RestlibException, re:
            log.info("REST Error.", exc_info=True)
            systemExit(re.code, re.msg)
        except SyncError, se:
            log.info("Sync Error: ", exc_info=True)
            systemExit("Error : %s" % se)
        except Exception, e:
            log.error("General Error: %s" % e)
            raise

    def _cancel_sync(self):
        if not self.options.id:
            print _("repo id required. Try --help")
            sys.exit(0)
        if not self.options.taskid:
            print _("task id required. Try --help")
            sys.exit(0)
        try:
            repos = self.pconn.cancel_sync(self.options.id, self.options.taskid)
            print _(" Sync task %s canceled") % self.options.taskid
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _delete(self):
        if not self.options.id:
            print _("repo id required. Try --help")
            sys.exit(0)
        try:
            self.pconn.delete(id=self.options.id)
            print _(" Successful deleted Repo [ %s ]") % self.options.id
        except RestlibException, re:
            print _(" Deleted operation failed on Repo [ %s ]") % self.options.id
            log.error("Error: %s" % re)
            sys.exit(-1)
        except Exception, e:
            print _(" Deleted operation failed on Repo [ %s ].") % self.options.id
            log.error("Error: %s" % e)
            sys.exit(-1)

    def _upload(self):
        (self.options, files) = self.parser.parse_args()
        # ignore the command and pick the files
        files = files[2:]
        if not self.options.id:
            print _("repo id required. Try --help")
            sys.exit(0)
        if self.options.dir:
            files += utils.processDirectory(self.options.dir, "rpm")
        if not files:
            print _("Need to provide at least one file to perform upload")
            sys.exit(0)
        uploadinfo = {}
        uploadinfo['repo'] = self.options.id
        for frpm in files:
            try:
                pkginfo = utils.processRPM(frpm)
            except FileError, e:
                print _('Error: %s') % e
                continue
            if not pkginfo.has_key('nvrea'):
                print _("Package %s is Not an RPM Skipping") % frpm
                continue
            pkgstream = base64.b64encode(open(frpm).read())
            try:
                status = self.pconn.upload(self.options.id, pkginfo, pkgstream)
                if status:
                    print _(" Successful uploaded [%s] to  Repo [ %s ]") % \
                        (pkginfo['pkgname'], self.options.id)
                else:
                    print _(" Failed to Upload [%s] to Repo [ %s ] ") % \
                            (pkginfo['pkgname'], self.options.id)
            except RestlibException, re:
                log.error("Error: %s" % re)
                raise #continue
            except Exception, e:
                log.error("Error: %s" % e)
                raise #continue

    def _schedules(self):
        print_header('Available Repository Schedules')
        schedules = self.pconn.all_schedules()
        for id in schedules.keys():
            print(constants.REPO_SCHEDULES_LIST % (id, schedules[id]))
