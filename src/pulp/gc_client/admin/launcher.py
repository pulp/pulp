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

from ConfigParser import SafeConfigParser
import logging
import logging.handlers
from optparse import OptionParser
import os
import sys

from   pulp.gc_client.framework.core import PulpPrompt, PulpCli, WIDTH_TERMINAL
from   pulp.gc_client.framework.extensions import ClientContext
import pulp.gc_client.framework.loader as extensions_loader

# -- constants ----------------------------------------------------------------

CONFIG_FILE = '/etc/pulp/admin/gc_admin.conf'

USER_DIR = '~/.pulp'
USER_LOG_FILE = 'admin.log'
USER_CONFIG = 'gc_admin.conf'

# -- configuration and logging ------------------------------------------------

def _load_configuration(filename):
    """
    @param filename: absolute path to the config file
    @type  filename: str

    @return: configuration object
    @rtype:  ConfigParser
    """
    # Calculate the override config filename
    full_user_dir = os.path.expanduser(USER_DIR)
    override_config = os.path.join(full_user_dir, USER_CONFIG)

    config = SafeConfigParser()
    config.read([filename, override_config])
    return config

def _initialize_logging(config, debug=False):
    """
    @return: configured logger
    """

    # Make sure the directory exists in the user's home
    full_log_dir = os.path.expanduser(USER_DIR)
    if not os.path.exists(full_log_dir):
        os.makedirs(full_log_dir)

    filename = os.path.join(full_log_dir, USER_LOG_FILE)

    pulp_log = logging.getLogger('pulp')
    pulp_log.addHandler(logging.handlers.RotatingFileHandler(filename, mode='w', maxBytes=1048576, backupCount=2))

    if debug:
        pulp_log.setLevel(logging.DEBUG)
    else:
        pulp_log.setLevel(logging.INFO)

    # Add the log file name to config so the rest of the app can access it for
    # output messages to the user
    config.add_section('logging')
    config.set('logging', 'filename', filename)

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

def _create_cli(prompt):
    """
    @return: cli instance used to drive the UI
    @rtype:  PulpCli
    """
    cli = PulpCli(prompt)
    return cli

def _create_shell(config, prompt):
    # Stub, will implement when we support a shell
    pass

# -- main execution -----------------------------------------------------------

def main():

    # Command line argument handling
    parser = OptionParser()
    parser.disable_interspersed_args()
    parser.add_option('--debug', dest='debug', action='store_true', default='False',
                      help='enables debug logging')
    parser.add_option('--config', dest='config', default=CONFIG_FILE,
                      help='absolute path to the configuration file; defaults to %s' % CONFIG_FILE)

    options, args = parser.parse_args()

    # Configuration and Logging
    config = _load_configuration(filename=options.config)
    logger = _initialize_logging(config, debug=options.debug)

    # UI Components (eventually this will decide between cli and shell)
    prompt = _create_prompt(config)
    cli = _create_cli(prompt)

    # REST Bindings
    server = None

    # Assemble the client context
    context = ClientContext(server, config, logger, prompt, cli=cli)

    # Load extensions into the UI in the context
    extensions_dir = config.get('general', 'extensions_dir')
    extensions_loader.load_extensions(extensions_dir, context)

    # Launch the appropriate UI (add in shell support here later)
    cli.run(args)

if __name__ == '__main__':
    sys.exit(main())