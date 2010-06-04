#
# Pulp client utility
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
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
import utils
from connection import RepoConnection, ConsumerConnection, RestlibException
import constants
from optparse import OptionParser, OptionGroup
from logutil import getLogger
import base64
import gettext
_ = gettext.gettext

log = getLogger(__name__)
## TODO: move this to config
CONSUMERID = "/etc/pulp/"

class BaseCore(object):
    """ Base class for all sub-calls. """
    def __init__(self, name="cli", usage=None, shortdesc=None,
            description=None):
        self.shortdesc = shortdesc
        if shortdesc is not None and description is None:
            description = shortdesc
        self.debug = 0
        self.parser = OptionParser(usage=usage, description=description)
        self._add_common_options()
        self.name = name

    def _add_common_options(self):
        """ Common options to all modules. """
        pass

    def _do_core(self):
        pass

    def main(self):
        (self.options, self.args) = self.parser.parse_args()
        self.args = self.args[1:]
        self._do_core()

class ConsumerCore(BaseCore):
    def __init__(self):
        usage = "usage: %prog consumer [OPTIONS]"
        shortdesc = "consumer specific actions to pulp server."
        desc = ""

        BaseCore.__init__(self, "consumer", usage, shortdesc, desc)
        self.actions = {"create" : "Create a consumer", 
                        "list"   : "List consumers", 
                        "delete" : "Delete a consumer", 
                        "bind"   : "Bind the consumer to listed repos",
                        "unbind" : "UnBind the consumer from repos"}
        self.name = "consumer"
        self.username = None
        self.password = None
        self.cconn = ConsumerConnection(host="localhost", port=8811)
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
            usage = "usage: %prog consumer create [OPTIONS]"
            BaseCore.__init__(self, "consumer create", usage, "", "")
            self.parser.add_option("--id", dest="id",
                           help="Consumer Identifier eg: foo.example.com")
            self.parser.add_option("--description", dest="description",
                           help="consumer description eg: foo's web server")
        if self.action == "bind":
            usage = "usage: %prog consumer bind [OPTIONS]"
            BaseCore.__init__(self, "consumer bind", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repo Identifier")
        if self.action == "unbind":
            usage = "usage: %prog consumer unbind [OPTIONS]"
            BaseCore.__init__(self, "consumer unbind", usage, "", "")
            self.parser.add_option("--repoid", dest="repoid",
                           help="Repo Identifier")
        if self.action == "list":
            usage = "usage: %prog consumer list [OPTIONS]"
            BaseCore.__init__(self, "consumer list", usage, "", "")
        if self.action == "delete":
            usage = "usage: %prog consumer delete [OPTIONS]"
            BaseCore.__init__(self, "consumer delete", usage, "", "")

    def _validate_options(self):
        pass

    def _usage(self):
        print "\nUsage: %s MODULENAME ACTION [options] --help\n" % os.path.basename(sys.argv[0])
        print "Supported Actions:\n"
        items = self.actions.items()
        #items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd))
        print("")

    def _do_core(self):
        self._validate_options()
        if self.action == "create":
            self._create()
        if self.action == "list":
            self._list()
        if self.action == "delete":
            self._delete()
        if self.action == "bind":
            self._bind()
        if self.action == "unbind":
            self._unbind()

    def _create(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.id:
            print("consumer id required. Try --help")
            sys.exit(0)
        if not self.options.description:
            self.options.description = self.options.id
        consumerinfo = {"id"   : self.options.id,
                    "description" : self.options.description,}
        try:
            consumer = self.cconn.create(consumerinfo)
            utils.writeToFile(os.path.join(CONSUMERID, "consumer"), consumer['id'])
            print _(" Successfully created Consumer [ %s ]" % consumer['id'])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _list(self):
        (self.options, self.args) = self.parser.parse_args()
        try:
            cons = self.cconn.consumers()
            columns = ["id", "description"]
            data = [ _sub_dict(con, columns) for con in cons]
            print """+-------------------------------------------+\n    List of Consumers \n+-------------------------------------------+"""
            for con in data:
                print constants.AVAILABLE_CONSUMER_LIST % (con["id"], con["description"])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _bind(self):
        print "Under Construction"

    def _unbind(self):
        print "under Construction"

    def _delete(self):
        print "under Construction"

class RepoCore(BaseCore):
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
                        "upload" : "Upload package(s) to this repo"}

        self.username = None
        self.password = None
        self.name = "repo"
        self.pconn = RepoConnection(host="localhost", port=8811)
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
        repoinfo = {"id"   : self.options.label,
                     "name" : self.options.name,
                     "arch" : self.options.arch,
                     "feed" : self.options.feed,}
        try:
            repo = self.pconn.create(repoinfo)
            print _(" Successfully created Repo [ %s ] with feed [ %s ]" % (repo['id'], repo["source"]))
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
            columns = ["id", "name", "source", "arch", "packages"]
            data = [ _sub_dict(repo, columns) for repo in repos]
            if not len(data):
                print _("No repos available to list")
                sys.exit(0)
            print """+-------------------------------------------+\n    List of Available Repositories \n+-------------------------------------------+"""
            for repo in data:
                repo["packages"] = _pkg_count(repo["packages"])
                print constants.AVAILABLE_REPOS_LIST % (repo["id"], repo["name"], repo["source"], repo["arch"], repo["packages"] )
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
            status = self.pconn.sync(self.options.label)
            if status:
                packages =  self.pconn.packages(self.options.label)
                pkg_count = _pkg_count(packages)
            print _(" Sync Successful. Repo [ %s ] now has a total of [ %s ] packages" % (self.options.label, pkg_count))
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _delete(self):
        (self.options, self.args) = self.parser.parse_args()
        if not self.options.label:
            print("repo label required. Try --help")
            sys.exit(0)
        try:
            status = self.pconn.delete(self.options.label)
            if status:
                print _(" Successful deleted Repo [ %s ] " % self.options.label)
            else:
                print _(" Deleted operation failed on Repo [ %s ] " % self.options.label)
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

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
                if debug: print("Package %s is Not an RPM Skipping" % frpm)
                continue
            uploadinfo['pkginfo']   = pkginfo
            uploadinfo['pkgstream'] = base64.b64encode(open(frpm).read())
            try:
                status = self.pconn.upload(uploadinfo)
                if status:
                    print _(" Successful uploaded [%s] to  Repo [ %s ] " % (pkginfo['pkgname'], self.options.label))
                else:
                    print _(" Faied to Upload %s to Repo [ %s ] " % self.options.label)
            except RestlibException, re:
                log.error("Error: %s" % re)
                continue
            except Exception, e:
                log.error("Error: %s" % e)
                continue
 

def _pkg_count(pkgdict):
    count =0
    for key, value in pkgdict.items():
        count += len(value["versions"])
    return count

def _sub_dict(datadict, subkeys, default=None) :
    return dict([ (k, datadict.get(k, default) ) for k in subkeys ] )

class FileError(Exception):
    pass

class CLI:
    """
     This is the main cli class that does command parsing like rho and matches
     the the right commands
    """
    def __init__(self):
        self.cli_cores = {}
        if len(sys.argv) > 2 and sys.argv[1] == "repo":
            self.cli_cores["repo"] = RepoCore()
        elif len(sys.argv) > 2 and sys.argv[1] == "consumer":
            self.cli_cores["consumer"] = ConsumerCore()
        else:
            for clazz in [ RepoCore, ConsumerCore]:
                cmd = clazz()
                # ignore the base class
                if cmd.name != "cli":
                    self.cli_cores[cmd.name] = cmd 


    def _add_core(self, cmd):
        self.cli_cores[cmd.name] = cmd

    def _usage(self):
        print "\nUsage: %s [options] MODULENAME --help\n" % os.path.basename(sys.argv[0])
        print "Supported modules:\n"

        # want the output sorted
        items = self.cli_cores.items()
        #items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd.shortdesc))
        print("")

    def _find_best_match(self, args):
        possiblecmd = []
        for arg in args[1:]:
            if not arg.startswith("-"):
                possiblecmd.append(arg)

        if not possiblecmd:
            return None

        cmd = None
        key = " ".join(possiblecmd)
        if self.cli_cores.has_key(" ".join(possiblecmd)):
            cmd = self.cli_cores[key]
        i = -1
        while cmd == None:
            key = " ".join(possiblecmd[:i])
            if key is None or key == "":
                break
            if self.cli_cores.has_key(key):
                cmd = self.cli_cores[key]
            i -= 1

        return cmd

    def main(self):
        if len(sys.argv) < 2 or not self._find_best_match(sys.argv):
            self._usage()
            sys.exit(0)

        cmd = self._find_best_match(sys.argv)
        if not cmd:
            self._usage()
            sys.exit(0)

        cmd.main()

def systemExit(code, msgs=None):
    "Exit with a code and optional message(s). Saved a few lines of code."

    if msgs:
        if type(msgs) not in [type([]), type(())]:
            msgs = (msgs, )
        for msg in msgs:
            sys.stderr.write(unicode(msg).encode("utf-8") + '\n')
    sys.exit(code)

if __name__ == "__main__":
    CLI().main()
