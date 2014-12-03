"""
Entry point for both the admin and consumer clients. The config file location
is passed in and its contents are used to drive the rest of the client execution.
"""

import errno
from gettext import gettext as _
import logging
import logging.handlers
from optparse import OptionParser
import os
import stat
import sys

from okaara.prompt import COLOR_CYAN, COLOR_LIGHT_CYAN

from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.client import constants
from pulp.client.extensions.core import PulpPrompt, PulpCli, ClientContext, WIDTH_TERMINAL
from pulp.client.extensions.exceptions import ExceptionHandler
import pulp.client.extensions.loader as extensions_loader
from pulp.common.config import Config


def main(config, exception_handler_class=ExceptionHandler):
    """
    Entry point into the launcher. Any extra necessary values will be pulled
    from the given configuration files.

    @param config: The CLI configuration.
    @type  config: Config

    @return: exit code suitable to return to the shell launching the client
    """
    ensure_user_pulp_dir()

    # Command line argument handling
    parser = OptionParser()
    parser.disable_interspersed_args()
    parser.add_option('-u', '--username', dest='username', action='store', default=None,
                      help=_('username for the Pulp server; if used will bypass the stored '
                             'certificate and override a username specified in ~/.pulp/admin.conf'))
    parser.add_option('-p', '--password', dest='password', action='store', default=None,
                      help=_('password for the Pulp server; must be used with --username. '
                             'if used will bypass the stored certificate and override a password '
                             'specified in ~/.pulp/admin.conf'))
    parser.add_option('--debug', dest='debug', action='store_true', default=False,
                      help=_('enables debug logging'))
    parser.add_option('--config', dest='config', default=None,
                      help=_('absolute path to the configuration file'))
    parser.add_option('--map', dest='print_map', action='store_true', default=False,
                      help=_('prints a map of the CLI sections and commands'))

    options, args = parser.parse_args()

    # Configuration and Logging
    if options.config is not None:
        config.update(Config(options.config))
    logger = _initialize_logging(config, debug=options.debug)

    # General UI pieces
    prompt = _create_prompt(config)
    exception_handler = exception_handler_class(prompt, config)

    # REST Bindings
    username = options.username
    password = options.password

    if not username and not password:
        # Try to get username/password from config if not explicitly set. username and password are
        # not included by default so we need to catch KeyError Exceptions.
        try:
            username = config['auth']['username']
            password = config['auth']['password']
        except KeyError:
            pass

    if username and not password:
        prompt_msg = 'Enter password: '
        password = prompt.prompt_password(_(prompt_msg))

        if password is prompt.ABORT:
            prompt.render_spacer()
            prompt.write(_('Login cancelled'))
            sys.exit(os.EX_NOUSER)

    server = _create_bindings(config, logger, username, password)

    # Client context
    context = ClientContext(server, config, logger, prompt, exception_handler)
    cli = PulpCli(context)
    context.cli = cli

    # Load extensions into the UI in the context
    extensions_dir = config['filesystem']['extensions_dir']
    extensions_dir = os.path.expanduser(extensions_dir)

    role = config['client']['role']
    try:
        extensions_loader.load_extensions(extensions_dir, context, role)
    except extensions_loader.LoadFailed, e:
        prompt.write(_('The following extensions failed to load: %(f)s' % {'f' : ', '.join(e.failed_packs)}))
        prompt.write(_('More information on the failures can be found in %(l)s' % {'l' : config['logging']['filename']}))
        return os.EX_OSFILE

    # Launch the appropriate UI (add in shell support here later)
    if options.print_map:
        cli.print_cli_map(section_color=COLOR_LIGHT_CYAN, command_color=COLOR_CYAN)
        return os.EX_OK
    else:
        code = cli.run(args)
        return code


def ensure_user_pulp_dir():
    """
    Creates ~/.pulp/ if it doesn't already exist.
    Writes a warning to stderr if ~/.pulp/ has unsafe permissions.

    This has to be run before the prompt object gets created, hence the old-school error reporting.

    Several other places try to access ~/.pulp, both from pulp-admin and pulp-consumer. The best
    we can do in order to create it once with the right permissions is to do call this function
    early.
    """
    path = os.path.expanduser(constants.USER_CONFIG_DIR)
    # 0700
    desired_mode = stat.S_IRUSR + stat.S_IWUSR + stat.S_IXUSR
    try:
        stats = os.stat(path)
        actual_mode = stat.S_IMODE(stats.st_mode)
        if actual_mode != desired_mode:
            sys.stderr.write(_('Warning: path should have mode 0700 because it may contain '
                               'sensitive information: %(p)s\n\n' % {'p': path}))

    except Exception, e:
        # if it doesn't exist, make it
        if isinstance(e, OSError) and e.errno == errno.ENOENT:
            try:
                os.mkdir(path, 0700)
            except Exception, e:
                sys.stderr.write(_('Failed to create path %(p)s: %(e)s\n\n' %
                                   {'p': path, 'e': str(e)}))
                sys.exit(1)
        else:
            sys.stderr.write(_('Failed to access path %(p)s: %(e)s\n\n' % {'p': path, 'e': str(e)}))
            sys.exit(1)


def _initialize_logging(config, debug=False):
    """
    @return: configured logger
    """

    filename = config['logging']['filename']
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


def _create_bindings(config, logger, username, password):
    """
    @return: bindings with a fully configured Pulp connection
    @rtype:  pulp.bindings.bindings.Bindings
    """

    # Extract all of the necessary values
    hostname = config['server']['host']
    port = int(config['server']['port'])

    cert_dir = config['filesystem']['id_cert_dir']
    cert_name = config['filesystem']['id_cert_filename']

    cert_dir = os.path.expanduser(cert_dir) # this will likely be in a user directory
    cert_filename = os.path.join(cert_dir, cert_name)

    # If the certificate doesn't exist, don't pass it to the connection creation
    if not os.path.exists(cert_filename):
        cert_filename = None

    call_log = None
    if config.has_option('logging', 'call_log_filename'):
        filename = config['logging']['call_log_filename']
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
    verify_ssl = config.parse_bool(config['server']['verify_ssl'])
    ca_path = config['server']['ca_path']
    conn = PulpConnection(
        hostname, port, username=username, password=password, cert_filename=cert_filename,
        logger=logger, api_responses_logger=call_log, verify_ssl=verify_ssl,
        ca_path=ca_path)
    bindings = Bindings(conn)

    return bindings


def _create_prompt(config):
    """
    @return: prompt instance to pass throughout the UI
    @rtype:  PulpPrompt
    """

    enable_color = config.parse_bool(config['output']['enable_color'])

    if config.parse_bool(config['output']['wrap_to_terminal']):
        wrap = WIDTH_TERMINAL
    else:
        wrap = int(config['output']['wrap_width'])

    prompt = PulpPrompt(enable_color=enable_color, wrap_width=wrap)
    return prompt
