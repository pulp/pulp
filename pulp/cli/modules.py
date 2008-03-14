"""
Pulp Command Line Modules

Optparse code used for parsing calls to the pulp command line interface.
Module here refers to the first argument in a call to pulp, i.e.

    pulp modulename --do-something

Copyright 2008, Red Hat, Inc
Devan Goodwin <dgoodwin@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

from pulp.model.contentmanager import DummyContentSourceContentManager 
from pulp.actions.reposync import RepoSync

HELP_FORMAT = "%-20s%s"

class CliModule:
    """
    Parent command line module class.
    """

    def help(self, parser):
        """
        Return a single line of help information for use when a user runs the
        parent pulp command line asking for help or without a module/args.
        """
        raise NotImplementedError

    def add_options(self, parser):
        """
        Modules add their own parser options. Must be implemented in child
        classes.
        """
        raise NotImplementedError

    def run(self, options):
        """
        Process a command send to this module.
        """
        raise NotImplementedError



class RepoModule(CliModule):

    def help(self):
        return HELP_FORMAT % ("pulp repo",
                "<--list|> [ARGS|--help]")

    def add_options(self, parser):

        parser.add_option("--list", action="store_true", dest="list",
            help="List all repositories.")
        parser.add_option("--sync-all", action="store_true", dest="sync_all",
            help="Sync all repositories.")


    def run(self, options):
        # TODO: Better way to do this with optparse?
        # Restrict to only one "sub-command":
        sub_commands = {
            options.list: self.__list,
            options.sync_all: self.__sync_all,
        }
        command_to_run = None
        for sub_command in sub_commands:
            if sub_command:
                if command_to_run is not None:
                    print "ERROR: Must specify only one sub-command"
                else:
                    command_to_run = sub_command

        # Run the command we identified:
        sub_commands[command_to_run](options)

    def __list(self, options):
        content_mgr = DummyContentSourceContentManager()
        repos = content_mgr.list_all_content_sources(None) # Subject?
        for repo in repos:
            print repo.name
            print "   %s" % repo.url

    def __sync_all(self, options):
        content_mgr = DummyContentSourceContentManager()
        repos = content_mgr.list_all_content_sources(None) # Subject?
        print "Syncing all repos:"
        reposync = RepoSync(repos)
        reposync.run()
    


