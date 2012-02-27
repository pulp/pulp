# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Entry point for the admin client.
"""

from   ConfigParser import SafeConfigParser
from   gettext import gettext as _
import logging
import logging.handlers
from   optparse import OptionParser
import os
import sys

from   pulp.gc_client.framework.core import PulpPrompt, PulpCli, WIDTH_TERMINAL, ClientContext
import pulp.gc_client.framework.loader as extensions_loader

# -- configuration and logging ------------------------------------------------

def _load_configuration(filename, override_filename):
    """
    @param filename: absolute path to the config file
    @type  filename: str

    @return: configuration object
    @rtype:  ConfigParser
    """

    # Calculate the override config filename
    config = SafeConfigParser()
    config.read([filename, override_filename])
    return config

def _initialize_logging(config, debug=False):
    """
    @return: configured logger
    """

    filename = config.get('logging', 'filename')
    filename = os.path.expanduser(filename)

    handler = logging.handlers.RotatingFileHandler(filename, mode='w', maxBytes=1048576, backupCount=2)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    pulp_log = logging.getLogger('pulp')
    pulp_log.addHandler(handler)

    if debug:
        pulp_log.setLevel(logging.DEBUG)
    else:
        pulp_log.setLevel(logging.INFO)

    return pulp_log

# -- ui components initialization ---------------------------------------------

def _create_prompt(config):
    """
    @return: prompt instance to pass throughout the UI
    @rtype:  PulpPrompt
    """

    enable_color = config.getboolean('output', 'enable_color')

    if config.getboolean('output', 'wrap_to_terminal'):
        wrap = WIDTH_TERMINAL
    else:
        wrap = config.getint('output', 'wrap_width')

    prompt = PulpPrompt(enable_color=enable_color, wrap_width=wrap)
    return prompt

def _create_cli(context):
    """
    @return: cli instance used to drive the UI
    @rtype:  PulpCli
    """
    cli = PulpCli(context)
    return cli

def _create_shell(context):
    # Stub, will implement when we support a shell
    pass

# -- main execution -----------------------------------------------------------

def main(config_filename, override_config_filename=None):

    # Command line argument handling
    parser = OptionParser()
    parser.disable_interspersed_args()
    parser.add_option('-u', '--username', dest='username', action='store', default=None,
                      help=_('credentials for the Pulp server; if specified will bypass the stored certificate'))
    parser.add_option('-p', '--password', dest='password', action='store', default=None,
                      help=_('credentials for the Pulp server; must be specified with --username'))
    parser.add_option('--debug', dest='debug', action='store_true', default='False',
                      help=_('enables debug logging'))
    parser.add_option('--config', dest='config', default=None,
                      help=_('absolute path to the configuration file; defaults to %(f)s' % {'f' : config_filename}))

    options, args = parser.parse_args()

    # Configuration and Logging
    if options.config is not None:
        config_filename = options.config
    config = _load_configuration(config_filename, override_config_filename)
    logger = _initialize_logging(config, debug=options.debug)

    # REST Bindings
    server = fake_bindings()

    # UI Components (eventually this will decide between cli and shell)
    prompt = _create_prompt(config)
    context = ClientContext(server, config, logger, prompt)
    cli = _create_cli(context)
    context.cli = cli

    # Assemble the client context

    # Load extensions into the UI in the context
    extensions_dir = config.get('filesystem', 'extensions_dir')
    extensions_dir = os.path.expanduser(extensions_dir)
    try:
        extensions_loader.load_extensions(extensions_dir, context)
    except extensions_loader.LoadFailed, e:
        prompt.write(_('The following extensions failed to load: %(f)s' % {'f' : ', '.join(e.failed_packs)}))
        prompt.write(_('More information on the failures can be found in %(l)s' % {'l' : config.get('logging', 'filename')}))
        return 1

    # Launch the appropriate UI (add in shell support here later)
    code = cli.run(args)

    return code

def fake_bindings():

    class RepoBindings:
        def list(self):
            repos = []

            for i in range(0, 3):
                r = {
                    'id' : 'repo-%d' % i,
                    'name' : 'Repo %d' % i,
                    'description' : 'Fake repository #%d' % i,
                }
                repos.append(r)

            return repos

    class Bindings:
        def __init__(self):
            self.repo = RepoBindings()

        def repo(self):
            return self.repo

    return Bindings()

if __name__ == '__main__':
    sys.exit(main())