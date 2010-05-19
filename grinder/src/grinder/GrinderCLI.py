#!/usr/bin/env python
#
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
import os
import sys
import optparse
import signal
import traceback
import logging
import GrinderLog
from optparse import OptionParser
from RepoFetch import YumRepoGrinder
from RHNSync import RHNSync

LOG = logging.getLogger("grinder.GrinderCLI")

class CliDriver(object):
    """ Base class for all sub-commands. """
    def __init__(self, name="cli", usage=None, shortdesc=None,
            description=None):
        self.shortdesc = shortdesc
        if shortdesc is not None and description is None:
            description = shortdesc
        self.debug = 0
        self.parser = OptionParser(usage=usage, description=description)
        self._add_common_options()
        self.name = name
        self.killcount = 0
        #GrinderLog.setup(self.debug)

    def _add_common_options(self):
        """ Add options that apply to all sub-commands. """
        self.parser.add_option("--debug", dest="debug",
                default=0, help="debug level")

    def _do_command(self):
        """ implement this in sub classes"""
        pass

    def stop(self):
        pass

    def main(self):

        (self.options, self.args) = self.parser.parse_args()
        self.args = self.args[1:]
        # do the work, catch most common errors here:
        self._do_command()

class RHNDriver(CliDriver):
    def __init__(self):
        usage = "usage: %prog rhn [OPTIONS]"
        shortdesc = "Fetches content from a rhn source."
        desc = "rhn"
        CliDriver.__init__(self, "rhn", usage, shortdesc, desc)
        GrinderLog.setup(self.debug)
        self.rhnSync = RHNSync()

        self.parser.add_option('-a', '--all', action='store_true', 
                help='Fetch ALL packages from a channel, not just latest')
        self.parser.add_option('-b', '--basepath', action='store', 
                help='Path RPMs are stored')
        self.parser.add_option('-c', '--certfile', action='store', 
                help='Entitlement Certificate')
        self.parser.add_option('-C', '--config', action='store', 
                help='Configuration file')
        self.parser.add_option('-k', '--kickstarts', action='store_true', 
                help='Sync all kickstart trees for channels specified')
        self.parser.add_option('-K', '--skippackages', action='store_true', 
                help='Skip sync of packages', default=False)
        self.parser.add_option('-L', '--listchannels', action='store_true', 
                help='List all channels we have access to synchronize')
        self.parser.add_option('-p', '--password', action='store',
                help='RHN Password')
        self.parser.add_option('-P', '--parallel', action='store',
                help='Number of threads to fetch in parallel.')
        self.parser.add_option('-r', '--removeold', action='store_true', 
                help='Remove older rpms')
        self.parser.add_option('-s', '--systemid', action='store', help='System ID')
        self.parser.add_option('-u', '--username', action='store', help='RHN User Account')
        self.parser.add_option('-U', '--url', action='store', help='Red Hat Server URL')

    def _validate_options(self):
        if self.options.all and self.options.removeold:
            systemExit(1, "Conflicting options specified 'all' and 'removeold'.")
        if self.options.config:
            if not self.rhnSync.loadConfig(self.options.config):
                systemExit(1, "Unable to parse config file: %s" % (self.options.config))
        if self.options.all:
            self.rhnSync.setFetchAllPackages(self.options.all)
        if self.options.basepath:
            self.rhnSync.setBasePath(self.options.basepath)
        if self.options.url:
            self.rhnSync.setURL(self.options.url)
        if self.options.username:
            self.rhnSync.setUsername(self.options.username)
        if self.options.password:
            self.rhnSync.setPassword(self.options.password)
        if self.options.certfile:
            cert = open(self.options.certfile, 'r').read()
            self.rhnSync.setCert(cert)
        if self.options.systemid:
            sysid = open(self.options.systemid, 'r').read()
            self.rhnSync.setSystemId(sysid)
        if self.options.parallel:
            self.rhnSync.setParallel(self.options.parallel)
        if self.options.debug:
            self.rhnSync.setVerbose(self.options.debug)
        if self.options.removeold:
            self.rhnSync.setRemoveOldPackages(self.options.removeold)

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()
        
        if self.options.listchannels:
            self.rhnSync.displayListOfChannels()
        else:
            # Check command line args for bad channel labels
            badChannels = self.rhnSync.checkChannels(self.args)
            if len(badChannels) > 0:
                LOG.critical("Bad channel labels: %s" % (badChannels))
                systemExit(1, "Please correct the channel labels you entered, then re-run")
            channels = self.rhnSync.getChannelSyncList()
            # Check config file for bad channel labels
            badChannels = self.rhnSync.checkChannels([x['label'] for x in channels])
            if len(badChannels) > 0:
                LOG.critical("Bad channel labels: %s" % (badChannels))
                systemExit(1, "Please correct the channel labels in: %s, then re-run" % (self.options.config))
            basePath = self.rhnSync.getBasePath()
            if not basePath:
                basePath = "./"
            for c in self.args:
                channels.append({'label':c, 'relpath':os.path.join(basePath,c)})
            report = {}
            for info in channels:
                label = info['label']
                savePath = info['relpath']
                report[label] = {}
                if not self.options.skippackages:
                    report[label]["packages"] = self.rhnSync.syncPackages(label, 
                            savePath, self.rhnSync.getVerbose())
                if self.options.kickstarts:
                    report[label]["kickstarts"] = self.rhnSync.syncKickstarts(label, 
                            savePath, self.rhnSync.getVerbose())
            for r in report:
                if report[r].has_key("packages"):
                    print "%s packages = %s" % (r, report[r]["packages"])
                if report[r].has_key("kickstarts"):
                    print "%s kickstarts = %s" % (r, report[r]["kickstarts"])

    def stop(self):
        self.rhnSync.stop()


class RepoDriver(CliDriver):
    parallel = 5
    def __init__(self):
        usage = "usage: %prog yum [OPTIONS]"
        shortdesc = "Fetches content from a yum repo."
        desc = "yum"
        CliDriver.__init__(self, "yum", usage, shortdesc, desc)
        GrinderLog.setup(self.debug)

        self.parser.add_option("--label", dest="label",
                          help="Repo label")
        self.parser.add_option("--url", dest="url",
                          help="Repo URL to fetch the content bits.")
        self.parser.add_option("--cacert", dest="cacert",
                          help="Path location to CA Certificate.")
        self.parser.add_option("--clicert", dest="clicert",
                          help="Path location to Client SSl Certificate.")
        self.parser.add_option("--clikey", dest="clikey",
                          help="Path location to Client Certificate Key.")
        self.parser.add_option("--parallel", dest="parallel",
                          help="Thread count to fetch the bits in parallel. Defaults to 5")
        self.parser.add_option("--dir", dest="dir",
                          help="Directory path to store the fetched content. Defaults to Current working Directory")

    def _validate_options(self):
        if not self.options.label:
            print("repo label is required. Try --help.")
            sys.exit(-1)

        if not self.options.url:
            print("No Url specific to fetch content. Try --help")
            sys.exit(-1)

        if self.options.parallel:
            self.parallel = self.options.parallel

    def _do_command(self):
        """
        Executes the command.
        """
        self._validate_options()
        if self.options.cacert and self.options.clicert and self.options.clikey:
            self.yfetch = YumRepoGrinder(self.options.label, self.options.url, \
                                self.parallel, cacert=self.options.cacert, \
                                clicert=self.options.clicert, clikey=self.options.clikey)
        else:
            self.yfetch = YumRepoGrinder(self.options.label, self.options.url, \
                                self.parallel)
        if self.options.dir:
            self.yfetch.fetchYumRepo(self.options.dir)
        else:
            self.yfetch.fetchYumRepo()

    def stop(self):
        self.yfetch.stop()

# this is similar to how rho does parsing
class CLI:
    def __init__(self):

        self.cli_commands = {}
        for clazz in [ RepoDriver, RHNDriver]:
            cmd = clazz()
            # ignore the base class
            if cmd.name != "cli":
                self.cli_commands[cmd.name] = cmd 


    def _add_command(self, cmd):
        self.cli_commands[cmd.name] = cmd

    def _usage(self):
        print "\nUsage: %s [options] MODULENAME --help\n" % os.path.basename(sys
.argv[0])
        print "Supported modules:\n"

        # want the output sorted
        items = self.cli_commands.items()
        items.sort()
        for (name, cmd) in items:
            print("\t%-14s %-25s" % (name, cmd.shortdesc))
        print("")

    def _find_best_match(self, args):
        """
        Returns the subcommand class that best matches the subcommand specified
        in the argument list. For example, if you have two commands that start
        with auth, 'auth show' and 'auth'. Passing in auth show will match
        'auth show' not auth. If there is no 'auth show', it tries to find
        'auth'.

        This function ignores the arguments which begin with --
        """
        possiblecmd = []
        for arg in args[1:]:
            if not arg.startswith("-"):
                possiblecmd.append(arg)

        if not possiblecmd:
            return None

        cmd = None
        key = " ".join(possiblecmd)
        if self.cli_commands.has_key(" ".join(possiblecmd)):
            cmd = self.cli_commands[key]

        i = -1
        while cmd == None:
            key = " ".join(possiblecmd[:i])
            if key is None or key == "":
                break

            if self.cli_commands.has_key(key):
                cmd = self.cli_commands[key]
            i -= 1

        return cmd

    def main(self):
        global cmd
        if len(sys.argv) < 2 or not self._find_best_match(sys.argv):
            self._usage()
            sys.exit(0)

        cmd = self._find_best_match(sys.argv)
        if not cmd:
            self._usage()
            sys.exit(0)
        cmd.main()

def handleKeyboardInterrupt(signalNumer, frame):
    if (cmd.killcount > 0):
        LOG.error("force quitting.")
        sys.exit()
    if (cmd.killcount == 0):
        cmd.killcount = 1
        msg = "SIGINT caught, will finish currently downloading" + \
              " packages and exit. Press CTRL+C again to force quit"
        LOG.error(msg)
        cmd.stop()

signal.signal(signal.SIGINT, handleKeyboardInterrupt)

def systemExit(code, msgs=None):
    "Exit with a code and optional message(s). Saved a few lines of code."
    if msgs:
        if type(msgs) not in [type([]), type(())]:
            msgs = (msgs, )
        for msg in msgs:
            sys.stderr.write(str(msg)+'\n')
    sys.exit(code)

if __name__ == "__main__":
    try:
        sys.exit(abs(CLI().main() or 0))
    except KeyboardInterrupt:
        systemExit(0, "\nUser interrupted process.")
