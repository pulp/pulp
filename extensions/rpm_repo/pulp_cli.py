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

from gettext import gettext as _
from urlparse import urlparse

from pulp.common.util import encode_unicode
from pulp.gc_client.api.responses import Response
from pulp.gc_client.framework.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag, PulpCliOptionGroup

# -- constants ----------------------------------------------------------------

IMPORTER_TYPE_ID = 'yum_importer'
DISTRIBUTOR_TYPE_ID = 'yum_distributor'

# ID the repo will use to refer to the automatically added yum distributor
DISTRIBUTOR_ID = DISTRIBUTOR_TYPE_ID

# Tuples of importer key name to more user-friendly CLI name. This must be a
# list of _all_ importer config values as the process of building up the
# importer config starts by extracting all of these values from the user args.
IMPORTER_CONFIG_KEYS = [
    ('feed_url', 'feed'),
    ('ssl_ca_cert', 'feed_ca_cert'),
    ('ssl_client_cert', 'feed_cert'),
    ('ssl_client_key', 'feed_key'),
    ('ssl_verify', 'verify_feed_ssl'),
    ('verify_size', 'verify_size'),
    ('verify_checksum', 'verify_checksum'),
    ('proxy_url', 'proxy_url'),
    ('proxy_port', 'proxy_port'),
    ('proxy_user', 'proxy_user'),
    ('proxy_pass', 'proxy_pass'),
    ('max_speed', 'max_speed'),
    ('num_threads', 'num_threads'),
]

DISTRIBUTOR_CONFIG_KEYS = [
    ('relative_url', 'relative_url'),
    ('http', 'serve_http'),
    ('https', 'serve_https'),
    ('gpgkey', 'gpg_key'),
    ('checksum_type', 'checksum_type'),
    ('auth_ca', 'auth_ca'),
    ('auth_cert', 'auth_cert'),
    ('https_ca', 'host_ca'),
]

LOG = None # set by context

# -- plugin hook --------------------------------------------------------------

def initialize(context):

    if not context.extension_config.getboolean('main', 'enabled'):
        return

    global LOG
    LOG = context.logger

    # Remove generic commands/sections that we want to override
    repo_section = context.cli.find_section('repo')
    repo_section.remove_command('create')
    repo_section.remove_command('update')
    repo_section.remove_command('list')
    repo_section.remove_command('delete')
    repo_section.remove_subsection('importer')

    # Add in overridden yum functionality
    repo_section.add_command(YumRepoCreateCommand(context))
    repo_section.add_command(YumRepoDeleteCommand(context))
    repo_section.add_command(YumRepoUpdateCommand(context))
    repo_section.add_command(YumRepoListCommand(context))

# -- command implementations --------------------------------------------------

class InvalidConfig(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass

class YumRepoCreateCommand(PulpCliCommand):
    def __init__(self, context):
        desc = 'creates a new repository that is configured to sync and publish RPM related content'
        PulpCliCommand.__init__(self, 'create', desc, self.create)

        self.context = context

        add_repo_options(self, False)

    def create(self, **kwargs):

        # All of the options will be present, even if the user didn't specify
        # them. Their values will be None, which the yum importer is set up
        # to handle.

        # Gather data
        repo_id = kwargs.pop('id')
        description = kwargs.pop('description', None)
        display_name = kwargs.pop('display_name', None)

        try:
            importer_config = args_to_importer_config(kwargs)
            distributor_config = args_to_distributor_config(kwargs)
        except InvalidConfig, e:
            self.context.prompt.render_failure_message(e[0])
            return

        # During create (but not update), if the relative path isn't specified
        # it is derived from the feed_url
        if 'relative_url' not in distributor_config:
            url_parse = urlparse(encode_unicode(importer_config['feed_url']))

            if url_parse[2] in ('', '/'):
                relative_path = '/' + repo_id
            else:
                relative_path = url_parse[2]
            distributor_config['relative_url'] = relative_path

        # Likely a temporary hack as we continue to refine how metadata generation
        # is done on the distributor
        distributor_config['generate_metadata'] = True

        # Package distributors for the call
        distributors = [(DISTRIBUTOR_TYPE_ID, distributor_config, True, DISTRIBUTOR_ID)]

        # Create the repository; let exceptions bubble up to the framework exception handler
        self.context.server.repo.create_and_configure(repo_id, display_name, description, None, IMPORTER_TYPE_ID, importer_config, distributors)

        self.context.prompt.render_success_message('Successfully created repository [%s]' % repo_id)

class YumRepoDeleteCommand(PulpCliCommand):
    def __init__(self, context):
        desc = 'deletes a repository'
        PulpCliCommand.__init__(self, 'delete', desc, self.delete)
        self.context = context

        self.add_option(PulpCliOption('--id', 'identifies the repository to delete', required=True))

    def delete(self, **kwargs):
        repo_id = kwargs['id']
        response = self.context.server.repo.delete(repo_id)

        if isinstance(response, Response):
            self.context.prompt.render_success_message(_('Repository [%(r)s] successfully deleted') % {'r' : repo_id})
        else:
            self.context.prompt.render_paragraph('Repository delete postponed due to other operation (eventually we\'ll show how to look this up later')

class YumRepoUpdateCommand(PulpCliCommand):
    def __init__(self, context):
        desc = 'updates an existing repository\'s configuration'
        PulpCliCommand.__init__(self, 'update', desc, self.update)

        self.context = context

        add_repo_options(self, True)

    def update(self, **kwargs):

        # Gather data
        repo_id = kwargs.pop('id')
        description = kwargs.pop('description', None)
        display_name = kwargs.pop('display_name', None)

        try:
            importer_config = args_to_importer_config(kwargs)
        except InvalidConfig, e:
            self.context.prompt.render_failure_message(e[0])
            return

        try:
            distributor_config = args_to_distributor_config(kwargs)
        except InvalidConfig, e:
            self.context.prompt.render_failure_message(e[0])
            return

        distributor_configs = {DISTRIBUTOR_ID : distributor_config}

        response = self.context.server.repo.update_repo_and_plugins(repo_id, display_name,
                   description, None, importer_config, distributor_configs)

        if isinstance(response, Response):
            self.context.prompt.render_success_message(_('Repository [%(r)s] successfully updated') % {'r' : repo_id})
        else:
            self.context.prompt.render_paragraph('Repository update postponed due to other operation (eventually we\'ll show how to look this up later')

class YumRepoListCommand(PulpCliCommand):

    def __init__(self, context):
        PulpCliCommand.__init__(self, 'list', 'lists repositories on the server', self.list)
        self.context = context
        self.prompt = context.prompt

        self.add_option(PulpCliFlag('--details', 'if specified, extra information on the repository will be displayed'))

    def list(self, **kwargs):
        self.prompt.render_title('Repositories')

        show_details = kwargs['details']

        repo_list = self.context.server.repo.repositories().response_body

        # Summary mode is default
        filters = ['id', 'display_name', 'description', 'content_unit_count', 'notes']

        if show_details:
            filters += ['sync_config', 'publish_config']

        # Process each repository to clean up/restructure various data
        for r in repo_list:

            # Pull the importer/distributor configs into the repo itself. For now
            # assume one of each since in the RPM commands we lock the user into
            # that. We may have to revisit the distributor part in the future.
            importers = r.pop('importers', None)
            distributors = r.pop('distributors', None)
            if show_details:

                # Extract the importer config
                if importers is not None and len(importers) > 0:
                    r['sync_config'] = importers[0]['config']

                    # Translate the importer config keys to cli counterparts
                    for importer_key, cli_key in IMPORTER_CONFIG_KEYS:
                        if importer_key in r['sync_config']:
                            r['sync_config'][cli_key] = r['sync_config'].pop(importer_key)

                    # Certificates are too long to display, so simply indicate if they
                    # are present. Eventually we can add a flag that will show them.
                    for key in ('feed_ca_cert', 'feed_cert', 'feed_key'):
                        if key in r['sync_config']:
                            r['sync_config'][key] = _('Yes')

                    # We don't want to display the proxy password in plain text, so
                    # if it's present swap it out with astericks
                    if 'proxy_pass' in r['sync_config']:
                        r['sync_config']['proxy_pass'] = '*' * len(r['sync_config']['proxy_pass'])

                # Extract the distributor config
                if distributors is not None and len(distributors) > 0:
                    r['publish_config'] = distributors[0]['config']

        self.prompt.render_document_list(repo_list, filters=filters, order=filters)

# -- utilities ----------------------------------------------------------------

def add_repo_options(command, is_update):
    """
    Adds options/flags for all repo configuration values (repo, importer, and
    distributor). This is meant to be called for both create and update commands
    to simplify consistency

    @param command: command to add options to
    """

    # Groups
    required_group = PulpCliOptionGroup('Required')
    basic_group = PulpCliOptionGroup('Basic')
    throttling_group = PulpCliOptionGroup('Throttling')
    ssl_group = PulpCliOptionGroup('Feed Authentication')
    verify_group = PulpCliOptionGroup('Verification')
    proxy_group = PulpCliOptionGroup('Feed Proxy')
    publish_group = PulpCliOptionGroup('Publishing')
    repo_auth_group = PulpCliOptionGroup('Client Authentication')

    # Order added indicates order in usage, so pay attention to this order when
    # dorking with it to make sure it makes sense
    command.add_option_group(required_group)
    command.add_option_group(basic_group)
    command.add_option_group(publish_group)
    command.add_option_group(ssl_group)
    command.add_option_group(repo_auth_group)
    command.add_option_group(verify_group)
    command.add_option_group(proxy_group)
    command.add_option_group(throttling_group)

    # Required Options
    required_group.add_option(PulpCliOption('--id', 'uniquely identifies the repository; only alphanumeric, -, and _ allowed', required=True))

    # Feed URL is special: required for create, optional for update
    if not is_update:
        feed_url_dest = required_group
    else:
        feed_url_dest = basic_group

    feed_url_dest.add_option(PulpCliOption('--feed', 'URL of the external source repository to sync', required=not is_update))

    # Metadata Options
    basic_group.add_option(PulpCliOption('--display_name', 'user-readable display name for the repository', required=False))
    basic_group.add_option(PulpCliOption('--description', 'user-readable description of the repo\'s contents', required=False))

    # Verify Options
    verify_group.add_option(PulpCliOption('--verify_size', 'if "true", the size of each synchronized file will be verified against the repo metadata; defaults to false', required=False))
    verify_group.add_option(PulpCliOption('--verify_checksum', 'if "true", the checksum of each synchronized file will be verified against the repo metadata; defaults to false', required=False))

    # Proxy Options
    proxy_group.add_option(PulpCliOption('--proxy_url', 'URL to the proxy server to use', required=False))
    proxy_group.add_option(PulpCliOption('--proxy_port', 'port on the proxy server to make requests', required=False))
    proxy_group.add_option(PulpCliOption('--proxy_user', 'username used to authenticate with the proxy server', required=False))
    proxy_group.add_option(PulpCliOption('--proxy_pass', 'password used to authenticate with the proxy server', required=False))

    # Throttling Options
    throttling_group.add_option(PulpCliOption('--max_speed', 'maximum bandwidth used per download thread, in KB/sec, when synchronizing the repo', required=False))
    throttling_group.add_option(PulpCliOption('--num_threads', 'number of threads that will be used to synchronize the repo', required=False))

    # SSL Options
    ssl_group.add_option(PulpCliOption('--feed_ca_cert', 'full path to the CA certificate that should be used to verify the external repo server\'s SSL certificate', required=False))
    ssl_group.add_option(PulpCliOption('--verify_feed_ssl', 'if "true", the feed\'s SSL certificate will be verified against the feed_ca_cert', required=False))
    ssl_group.add_option(PulpCliOption('--feed_cert', 'full path to the certificate to use for authentication when accessing the external feed', required=False))
    ssl_group.add_option(PulpCliOption('--feed_key', 'full path to the private key for feed_cert', required=False))

    # Publish Options
    publish_group.add_option(PulpCliOption('--relative_url', 'relative path the repository will be served from; defaults to relative path of the feed URL', required=False))
    publish_group.add_option(PulpCliOption('--serve_http', 'if "true", the repository will be served over HTTP; defaults to false', required=False, default='false'))
    publish_group.add_option(PulpCliOption('--serve_https', 'if "true", the repository will be served over HTTPS; defaults to true', required=False, default='true'))
    publish_group.add_option(PulpCliOption('--checksum_type', 'type of checksum to use during metadata generation', required=False))
    publish_group.add_option(PulpCliOption('--gpg_key', 'GPG key used to sign and verify packages in the repository', required=False))

    # Publish Security Options
    repo_auth_group.add_option(PulpCliOption('--host_ca', 'full path to the CA certificate that signed the repository hosts\'s SSL certificate when serving over HTTPS', required=False))
    repo_auth_group.add_option(PulpCliOption('--auth_ca', 'full path to the CA certificate that should be used to verify client authentication certificates; setting this turns on client authentication for the repository', required=False))
    repo_auth_group.add_option(PulpCliOption('--auth_cert', 'full path to the entitlement certificate that will be given to bound consumers to grant access to this repository', required=False))

def args_to_importer_config(kwargs):
    """
    Takes the arguments read from the CLI and converts the client-side input
    to the server-side expectations. The supplied dict will not be modified.

    @return: config to pass into the add/update importer calls
    @raise InvalidConfig: if one or more arguments is not valid for the importer
    """

    importer_config = _prep_config(kwargs, IMPORTER_CONFIG_KEYS)

    # Parsing of true/false
    boolean_arguments = ('ssl_verify', 'verify_size', 'verify_checksum')
    _convert_boolean_arguments(boolean_arguments, importer_config)

    # Read in the contents of any files that were specified
    file_arguments = ('ssl_ca_cert', 'ssl_client_cert', 'ssl_client_key')
    _convert_file_contents(file_arguments, importer_config)

    LOG.debug('Importer configuration options')
    LOG.debug(importer_config)

    return importer_config

def args_to_distributor_config(kwargs):
    """
    Takes the arguments read from the CLI and converts the client-side input
    to the server-side expectations. The supplied dict will not be modified.

    @return: config to pass into the add/update distributor calls
    @raise InvalidConfig: if one or more arguments is not valid for the distributor
    """
    distributor_config = _prep_config(kwargs, DISTRIBUTOR_CONFIG_KEYS)

    # Parsing of true/false
    boolean_arguments = ('http', 'https')
    _convert_boolean_arguments(boolean_arguments, distributor_config)

    # Read in the contents of any files that were specified
    file_arguments = ('auth_cert', 'auth_ca', 'https_ca', 'gpgkey')
    _convert_file_contents(file_arguments, distributor_config)

    # There is an explicit flag for enabling/disabling repository protection.
    # This may be useful to expose to the user to quickly turn on/off repo
    # auth for debugging purposes. For now, if the user has specified an auth
    # CA, assume they also want to flip that protection flag to true.
    if 'auth_ca' in distributor_config:
        if distributor_config['auth_ca'] is None:
            # This would occur if the user requested to remove the CA (as
            # compared to not mentioning it at all, which is the outer if statement.
            distributor_config['protected'] = False
        else:
            # If there is something in the CA, assume it's turning on auth and
            # flip the flag to true.
            distributor_config['protected'] = True

    LOG.debug('Distributor configuration options')
    LOG.debug(distributor_config)

    return distributor_config

def _prep_config(kwargs, plugin_config_keys):
    """
    Performs common initialization for both importer and distributor config
    parsing. The common conversion includes:

    * Create a base config dict pulling the given plugin_config_keys from the
      user-specified arguments
    * Translate the client-side argument names into the plugin expected keys
    * Strip out any None values which means the user did not specify the
      argument in the call
    * Convert any empty strings into None which represents the user removing
      the config value

    @param plugin_config_keys: one of the *_CONFIG_KEYS constants
    @return: dictionary to use as the basis for the config
    """

    # Populate the plugin config with the plugin-relevant keys in the user args
    user_arg_keys = [k[1] for k in plugin_config_keys]
    plugin_config = dict([(k, v) for k, v in kwargs.items() if k in user_arg_keys])

    # Simple name translations
    for plugin_key, cli_key in plugin_config_keys:
        plugin_config[plugin_key] = plugin_config.pop(cli_key, None)

    # Strip out anything with a None value. The way the parser works, all of
    # the possible options will be present with None as the value. Strip out
    # everything with a None value now as it means it hasn't been specified
    # by the user (removals are done by specifying ''.
    plugin_config = dict([(k, v) for k, v in plugin_config.items() if v is not None])

    # Now convert any "" strings into None. This should be safe in all cases and
    # is the mechanic used to get "remove config option" semantics.
    convert_keys = [k for k in plugin_config if plugin_config[k] == '']
    for k in convert_keys:
        plugin_config[k] = None

    return plugin_config

def _convert_boolean_arguments(boolean_keys, config):
    """
    For each given key, if it is in the config this call will attempt to convert
    the user-provided text for true/false into an actual boolean. The boolean
    value is stored directly in the config and replaces the text version. If the
    key is not present or is None, this method does nothing for that key. If the
    value for a key isn't parsable into a boolean, an InvalidConfig exception
    is raised with a pre-formatted message indicating such.

    @param boolean_keys: list of keys to convert in the given config
    """

    for key in boolean_keys:
        if key not in config or config[key] is None:
            continue
        v = config.pop(key)
        if v.strip().lower() == 'true':
            config[key] = True
            continue
        if v.strip().lower() == 'false':
            config[key] = False
            continue
        raise InvalidConfig(_('Value for %(f)s must be either true or false' % {'f' : key}))

def _convert_file_contents(file_keys, config):
    """
    For each given key, if it is in the config this call will attempt to read
    the file indicated by the key value. The contents of the file are stored
    directly in the config and replaces the filename itself. If the key is not
    present or is None, this method does nothing for that key. If the value for
    the key cannot be read in as a file, an InvalidConfig exception is raised
    with a pre-formatted message indicating such.

    @param file_keys: list of keys to read in as files
    """

    for key in file_keys:
        if key in config and config[key] is not None:
            filename = config[key]
            try:
                f = open(filename)
                contents = f.read()
                f.close()

                config[key] = contents
            except:
                raise InvalidConfig(_('File [%(f)s] cannot be read' % {'f' : filename}))

