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
Entry point for both the admin and consumer clients. The config file location
is passed in and its contents are used to drive the rest of the client execution.
"""

from   ConfigParser import SafeConfigParser
from   gettext import gettext as _
import logging
import logging.handlers
from   optparse import OptionParser
import os

from   okaara.prompt import COLOR_CYAN, COLOR_LIGHT_CYAN

from   pulp.client.extensions.core import PulpPrompt, PulpCli, ClientContext, WIDTH_TERMINAL
from   pulp.client.extensions.exceptions import ExceptionHandler
import pulp.client.extensions.loader as extensions_loader
from   pulp.bindings.bindings import Bindings
from   pulp.bindings.server import PulpConnection

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

    # Make sure the parent directories for the log files exist
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    handler = logging.handlers.RotatingFileHandler(filename, mode='w', maxBytes=1048576, backupCount=2)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    pulp_log = logging.getLogger('pulp')
    pulp_log.addHandler(handler)

    if debug:
        pulp_log.setLevel(logging.DEBUG)
    else:
        pulp_log.setLevel(logging.INFO)

    return pulp_log

# -- server connection --------------------------------------------------------

def _create_bindings(config, logger, username, password):
    """
    @return: bindings with a fully configured Pulp connection
    """

    # Extract all of the necessary values
    hostname = config.get('server', 'host')
    port = config.getint('server', 'port')

    cert_dir = config.get('filesystem', 'id_cert_dir')
    cert_name = config.get('filesystem', 'id_cert_filename')

    cert_dir = os.path.expanduser(cert_dir) # this will likely be in a user directory
    cert_filename = os.path.join(cert_dir, cert_name)

    # If the certificate doesn't exist, don't pass it to the connection creation
    if not os.path.exists(cert_filename):
        cert_filename = None

    call_log = None
    if config.has_option('logging', 'call_log_filename'):
        filename = config.get('logging', 'call_log_filename')
        filename = os.path.expanduser(filename) # also likely in a user dir

        # Make sure the parent directories for the log files exist
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        handler = logging.handlers.RotatingFileHandler(filename, mode='w', maxBytes=1048576, backupCount=2)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        call_log = logging.getLogger('call_log')
        call_log.addHandler(handler)
        call_log.setLevel(logging.INFO)

    # Create the connection and bindings
    conn = PulpConnection(hostname, port, username=username, password=password, cert_filename=cert_filename, logger=logger, api_responses_logger=call_log)
    bindings = Bindings(conn)

    return bindings

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

# -- main execution -----------------------------------------------------------

def main(config_filename, override_config_filename=None):
    """
    Entry point into the launcher. Any extra necessary values will be pulled
    from the given configuration files.

    @param config_filename: full path to the config file
    @param override_config_filename: full path; values will override those in the
           base config

    @return: exit code suitable to return to the shell launching the client
    """

    # Command line argument handling
    parser = OptionParser()
    parser.disable_interspersed_args()
    parser.add_option('-u', '--username', dest='username', action='store', default=None,
                      help=_('credentials for the Pulp server; if specified will bypass the stored certificate'))
    parser.add_option('-p', '--password', dest='password', action='store', default=None,
                      help=_('credentials for the Pulp server; must be specified with --username'))
    parser.add_option('--debug', dest='debug', action='store_true', default=False,
                      help=_('enables debug logging'))
    parser.add_option('--config', dest='config', default=None,
                      help=_('absolute path to the configuration file; defaults to %(f)s' % {'f' : config_filename}))
    parser.add_option('--map', dest='print_map', action='store_true', default=False,
                      help=_('prints a map of the CLI sections and commands'))

    options, args = parser.parse_args()

    # Configuration and Logging
    if options.config is not None:
        config_filename = options.config
    config = _load_configuration(config_filename, override_config_filename)
    logger = _initialize_logging(config, debug=options.debug)

    # REST Bindings
    server = _create_bindings(config, logger, options.username, options.password)

    # Client context
    prompt = _create_prompt(config)
    exception_handler = ExceptionHandler(prompt, config)
    context = ClientContext(server, config, logger, prompt, exception_handler)
    cli = PulpCli(context)
    context.cli = cli

    # Load extensions into the UI in the context
    extensions_dir = config.get('filesystem', 'extensions_dir')
    extensions_dir = os.path.expanduser(extensions_dir)
    try:
        extensions_loader.load_extensions(extensions_dir, context)
    except extensions_loader.LoadFailed, e:
        prompt.write(_('The following extensions failed to load: %(f)s' % {'f' : ', '.join(e.failed_packs)}))
        prompt.write(_('More information on the failures can be found in %(l)s' % {'l' : config.get('logging', 'filename')}))
        return os.EX_OSFILE

    # Launch the appropriate UI (add in shell support here later)
    if options.print_map:
        cli.print_cli_map(section_color=COLOR_LIGHT_CYAN, command_color=COLOR_CYAN)
        return os.EX_OK
    else:
        code = cli.run(args)
        return code
