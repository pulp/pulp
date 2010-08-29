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

import os
import sys
import time
import base64

import pulp.client.utils as utils
import pulp.client.constants as constants
from pulp.client.core.basecore import BaseCore, systemExit
from pulp.client.connection import RepoConnection, RestlibException
from pulp.client.logutil import getLogger
from pulp.client.config import Config
CFG = Config()

import gettext
_ = gettext.gettext
log = getLogger(__name__)

class repo(BaseCore):
    def __init__(self, actions=None):
        usage = "repo [OPTIONS]"
        shortdesc = "repository specifc actions to pulp server."
        desc = ""
        self.name = "repo"
        self.actions = actions or {"create"     : "Create a repo",
                                   "update"     : "Update a repo",
                                   "list"       : "List available repos",
                                   "delete"     : "Delete a repo",
                                   "sync"       : "Sync data to this repo from the feed",
                                   "cancel_sync": "Cancel a running sync",
                                   "upload"     : "Upload package(s) to this repo",
                                   "schedules"  : "List all repo schedules", }
        BaseCore.__init__(self, "repo", usage, shortdesc, desc)

    def load_server(self):
        self.pconn = RepoConnection(host=CFG.server.host or "localhost",
                                    port=CFG.server.port or 443,
                                    username=self.username,
                                    password=self.password,
                                    cert_file=self.cert_filename,
                                    key_file=self.key_filename)
    def generate_options(self):
        self.action = self._get_action()
        if self.action == "create":
            usage = "repo create [OPTIONS]"
            self.setup_option_parser(usage, "", True)
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
                           help="Use symlinks instead of copying bits locally. \
                            Applicable for local syncs")
        if self.action == "sync":
            usage = "repo sync [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="Repository Id")
            self.parser.add_option("--timeout", dest="timeout",
                           help="Sync Timeout")
        if self.action == "cancel_sync":
            usage = "repo cancel_sync [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="Repository Id")
            self.parser.add_option("--taskid", dest="taskid",
                           help="Task ID")
        if self.action == "delete":
            usage = "repo delete [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="Repository Id")
        if self.action == "list":
            usage = "repo list [OPTIONS]"
            self.setup_option_parser(usage, "", True)
        if self.action == "upload":
            usage = "repo upload [OPTIONS] <package>"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="Repository Id")
            self.parser.add_option("--dir", dest="dir",
                           help="Process packages from this directory")
        if self.action == "schedules":
            usage = "repo schedules"
            self.setup_option_parser(usage, "", True)

    def _do_core(self):
        if self.action == "create":
            self._create()
        if self.action == "list":
            self._list()
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

    def _create(self):
        if not self.options.id:
            print("repo id required. Try --help")
            sys.exit(0)
        if not self.options.name:
            self.options.name = self.options.id
        if not self.options.arch:
            self.options.arch = "noarch"

        symlinks = False
        if self.options.symlinks:
            symlinks = self.options.symlinks

        cert_data = None
        if self.options.cacert and self.options.cert and self.options.key:
            cert_data = {"ca" : utils.readFile(self.options.cacert),
                         "cert"    : utils.readFile(self.options.cert),
                         "key"     : utils.readFile(self.options.key)}

        try:
            repo = self.pconn.create(self.options.id, self.options.name, \
                                     self.options.arch, self.options.feed, \
                                     symlinks, self.options.schedule, cert_data=cert_data)
            print _(" Successfully created Repo [ %s ]" % repo['id'])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            systemExit(e.code, e.msg)

    def _list(self):
        try:
            repos = self.pconn.repositories()
            if not len(repos):
                print _("No repos available to list")
                sys.exit(0)
            print """+-------------------------------------------+\n    List of Available Repositories \n+-------------------------------------------+"""
            for repo in repos:
                #repo["packages"] = repo["packages"]
                print constants.AVAILABLE_REPOS_LIST % (repo["id"], repo["name"],
                                                        repo["source"], repo["arch"],
                                                        repo["sync_schedule"], repo["packages"])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _sync(self):
        if not self.options.id:
            print("repo id required. Try --help")
            sys.exit(0)
        try:
            task_object = self.pconn.sync(self.options.id, self.options.timeout)
            state = "waiting"
            print "Task created with ID::", task_object['id']
            while state not in ["finished", "error", 'timed out', 'canceled']:
                time.sleep(5)
                status = self.pconn.sync_status(task_object['status_path'])
                if status is None:
                    raise SyncError(_('No sync for repository [%s] found') % self.options.id)
                state = status['state']
                print "Sync Status::", state
            packages = self.pconn.packages(self.options.id)
            pkg_count = 0
            if packages:
                pkg_count = len(packages)
            if state == "error":
                raise SyncError(status['traceback'][-1])
            else:
                print _(" Sync Successful. Repo [ %s ] now has a total of [ %s ] packages" % (self.options.id, pkg_count))
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
            print("repo id required. Try --help")
            sys.exit(0)
        if not self.options.taskid:
            print("task id required. Try --help")
            sys.exit(0)
        try:
            repos = self.pconn.cancel_sync(self.options.id, self.options.taskid)
            print _(" Sync task %s cancelled") % self.options.taskid
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _delete(self):
        if not self.options.id:
            print("repo id required. Try --help")
            sys.exit(0)
        try:
            self.pconn.delete(id=self.options.id)
            print _(" Successful deleted Repo [ %s ] " % self.options.id)
        except RestlibException, re:
            print _(" Deleted operation failed on Repo [ %s ] " % \
                  self.options.id)
            log.error("Error: %s" % re)
            sys.exit(-1)
        except Exception, e:
            print _(" Deleted operation failed on Repo [ %s ]. " % \
                  self.options.id)
            log.error("Error: %s" % e)
            sys.exit(-1)

    def _upload(self):
        (self.options, files) = self.parser.parse_args()
        # ignore the command and pick the files
        files = files[2:]
        if not self.options.id:
            print("repo id required. Try --help")
            sys.exit(0)
        if self.options.dir:
            files += utils.processDirectory(self.options.dir, "rpm")
        if not files:
            print("Need to provide atleast one file to perform upload")
            sys.exit(0)
        uploadinfo = {}
        uploadinfo['repo'] = self.options.id
        for frpm in files:
            try:
                pkginfo = utils.processRPM(frpm)
            except FileError, e:
                print('Error: %s' % e)
                continue
            if not pkginfo.has_key('nvrea'):
                print("Package %s is Not an RPM Skipping" % frpm)
                continue
            pkgstream = base64.b64encode(open(frpm).read())
            try:
                status = self.pconn.upload(self.options.id, pkginfo, pkgstream)
                if status:
                    print _(" Successful uploaded [%s] to  Repo [ %s ] " % (pkginfo['pkgname'], self.options.id))
                else:
                    print _(" Failed to Upload %s to Repo [ %s ] " % self.options.id)
            except RestlibException, re:
                log.error("Error: %s" % re)
                raise #continue
            except Exception, e:
                log.error("Error: %s" % e)
                raise #continue

    def _schedules(self):
        print("""+-------------------------------------+\n    Available Repository Schedules \n+-------------------------------------+""")

        schedules = self.pconn.all_schedules()
        for id in schedules.keys():
            print(constants.REPO_SCHEDULES_LIST % (id, schedules[id]))


class FileError(Exception):
    pass

class SyncError(Exception):
    pass
