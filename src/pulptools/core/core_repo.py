#!/usr/bin/python
#
# Pulp Repo management module
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>

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

import pulptools.utils as utils
import pulptools.constants as constants
from pulptools.core.basecore import BaseCore, systemExit
from pulptools.connection import RepoConnection, RestlibException
from pulptools.logutil import getLogger
from pulptools.config import Config
CFG = Config()

import gettext
_ = gettext.gettext
log = getLogger(__name__)

class repo(BaseCore):
    def __init__(self):
        usage = "usage: %prog repo [OPTIONS]"
        shortdesc = "repository specifc actions to pulp server."
        desc = ""

        BaseCore.__init__(self, "repo", usage, shortdesc, desc)
        self.actions = {"create" : "Create a repo", 
                        "update" : "Update a repo", 
                        "list"   : "List available repos", 
                        "delete" : "Delete a repo", 
                        "sync"   : "Sync data to this repo from the feed",
                        "upload" : "Upload package(s) to this repo",
                        "schedules" : "List all repo schedules",}

        self.username = None
        self.password = None
        self.name = "repo"
        self.pconn = RepoConnection(host=CFG.server.host or "localhost", 
                                    port=CFG.server.port or 8811)
        self.generate_options()

    def generate_options(self):

        possiblecmd = []

        for arg in sys.argv[1:]:
            if not arg.startswith("-"):
                possiblecmd.append(arg)
        self.action = None
        if len(possiblecmd) > 1:
            self.action = possiblecmd[1]
        elif len(possiblecmd) == 1 and possiblecmd[0] == self.name:
            self._usage()
            sys.exit(0)
        else:
            return
        if self.action not in self.actions.keys():
            self._usage()
            sys.exit(0)
        if self.action == "create":
            usage = "usage: %prog repo create [OPTIONS]"
            BaseCore.__init__(self, "repo create", usage, "", "")
            self.parser.add_option("--label", dest="label",
                           help="Repository Label")
            self.parser.add_option("--name", dest="name",
                           help="common repository name")
            self.parser.add_option("--arch", dest="arch",
                           help="package arch the repo should support.")
            self.parser.add_option("--feed", dest="feed",
                           help="Url feed to populate the repo")
            self.parser.add_option("--schedule", dest="schedule",
                           help="Schedule for automatically synchronizing the repository")
            self.parser.add_option("--symlinks", action="store_true", dest="symlinks",
                           help="Use symlinks instead of copying bits locally. \
                            Applicable for local syncs")
        if self.action == "sync":
            usage = "usage: %prog repo sync [OPTIONS]"
            BaseCore.__init__(self, "repo sync", usage, "", "")
            self.parser.add_option("--label", dest="label",
                           help="Repository Label")
        if self.action == "delete":
            usage = "usage: %prog repo delete [OPTIONS]"
            BaseCore.__init__(self, "repo delete", usage, "", "")
            self.parser.add_option("--label", dest="label",
                           help="Repository Label")
        if self.action == "list":
            usage = "usage: %prog repo list [OPTIONS]"
            BaseCore.__init__(self, "repo list", usage, "", "")
        if self.action == "upload":
            usage = "usage: %prog repo upload [OPTIONS] <package>"
            BaseCore.__init__(self, "repo upload", usage, "", "")
            self.parser.add_option("--label", dest="label",
                           help="Repository Label")
            self.parser.add_option("--dir", dest="dir",
                           help="Process packages from this directory")
        if self.action == "schedules":
            usage = "usage: %prog repo schedules"
            BaseCore.__init__(self, "repo schedules", usage, "", "")

    def _validate_options(self):
        pass

    def _usage(self):
        print "\nUsage: %s MODULENAME ACTION [options] --help\n" % os.path.basename(sys.argv[0])
        print "Supported Actions:\n"
        items = self.actions.items()
        items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd))
        print("")

    def _do_core(self):
        self._validate_options()
        if self.action == "create":
            self._create()
        if self.action == "list":
            self._list()
        if self.action == "sync":
            self._sync()
        if self.action == "delete":
            self._delete()
        if self.action == "upload":
            self._upload()
        if self.action == "schedules":
            self._schedules()

    def _create(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.label:
            print("repo label required. Try --help")
            sys.exit(0)
        if not self.options.name:
            self.options.name = self.options.label
        if not self.options.arch:
            self.options.arch = "noarch"
        if not self.options.feed:
            print("repo feed required. Try --help")
            sys.exit(0)
        symlinks = False
        if self.options.symlinks:
            symlinks = self.options.symlinks
        try:
            repo = self.pconn.create(self.options.label, self.options.name, \
                                     self.options.arch, self.options.feed, \
                                     symlinks, self.options.schedule)
            print _(" Successfully created Repo [ %s ] with feed [ %s ]" % \
                                     (repo['id'], repo["source"]))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            systemExit(e.code, e.msg)

    def _list(self):
        (self.options, self.args) = self.parser.parse_args()
        try:
            repos = self.pconn.repositories()
            columns = ["id", "name", "source", "arch", "sync_schedule", "packages", "packagegroupcategories", "packagegroups"]
            data = [ _sub_dict(repo, columns) for repo in repos]
            if not len(data):
                print _("No repos available to list")
                sys.exit(0)
            print """+-------------------------------------------+\n    List of Available Repositories \n+-------------------------------------------+"""
            for repo in data:
                repo["packages"] = len(repo["packages"])
                repo["packagegroupcategories"] = repo["packagegroupcategories"].keys()
                repo["packagegroups"] = len(repo["packagegroups"])
                print constants.AVAILABLE_REPOS_LIST % (repo["id"], repo["name"],
                                                        repo["source"], repo["arch"],
                                                        repo["sync_schedule"], repo["packages"],
                                                        repo["packagegroupcategories"], repo["packagegroups"])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _sync(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.label:
            print("repo label required. Try --help")
            sys.exit(0)
        try:
            task_object = self.pconn.sync(self.options.label)
            state = "waiting"
            while state not in ["finished", "error"]:
                time.sleep(5)
                status = self.pconn.sync_status(task_object['status_path'])
                state= status['state']
                print "Sync Status::",state
            packages =  self.pconn.packages(self.options.label)
            pkg_count = len(packages)
            if state == "error":
                raise SyncError(status['traceback'][-1])
            else:
                print _(" Sync Successful. Repo [ %s ] now has a total of [ %s ] packages" % (self.options.label, pkg_count))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except SyncError, se:
            log.error("Error: %s" % se)
            systemExit("Error : %s" % se)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _delete(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.label:
            print("repo label required. Try --help")
            sys.exit(0)
        try:
            self.pconn.delete(id=self.options.label)
            print _(" Successful deleted Repo [ %s ] " % self.options.label)
        except RestlibException, re:
            print _(" Deleted operation failed on Repo [ %s ] " % \
                  self.options.label)
            log.error("Error: %s" % re)
            sys.exit(-1)
        except Exception, e:
            print _(" Deleted operation failed on Repo [ %s ]. " % \
                  self.options.label)
            log.error("Error: %s" % e)
            sys.exit(-1)

    def _upload(self):
        (self.options, files) = self.parser.parse_args()
        # ignore the command and pick the files
        files = files[2:]
        if not self.options.label:
            print("repo label required. Try --help")
            sys.exit(0)
        if self.options.dir:
            files += utils.processDirectory(self.options.dir, "rpm")
        if not files:
            print("Need to provide atleast one file to perform upload")
            sys.exit(0)
        uploadinfo = {}
        uploadinfo['repo'] = self.options.label
        for frpm in files:
            try: 
                pkginfo = utils.processFile(frpm)
            except FileError, e:
                print('Error: %s' % e)
                continue
            if not pkginfo.has_key('nvrea'):
                print("Package %s is Not an RPM Skipping" % frpm)
                continue
            pkgstream = base64.b64encode(open(frpm).read())
            try:
                status = self.pconn.upload(self.options.label, pkginfo, pkgstream)
                if status:
                    print _(" Successful uploaded [%s] to  Repo [ %s ] " % (pkginfo['pkgname'], self.options.label))
                else:
                    print _(" Failed to Upload %s to Repo [ %s ] " % self.options.label)
            except RestlibException, re:
                log.error("Error: %s" % re)
                raise #continue
            except Exception, e:
                log.error("Error: %s" % e)
                raise #continue
 
    def _schedules(self):
        print("""+-------------------------------------+\n    Available Repository Schedules \n+-------------------------------------+""")

        schedules = self.pconn.all_schedules()
        for label in schedules.keys():
            print(constants.REPO_SCHEDULES_LIST % (label, schedules[label]))

def _sub_dict(datadict, subkeys, default=None) :
    return dict([ (k, datadict.get(k, default) ) for k in subkeys ] )

class FileError(Exception):
    pass

class SyncError(Exception):
    pass
