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
from pulp.gc_client.framework.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag, PulpCliOptionGroup
from pulp.gc_client.util.arg_utils import InvalidConfig, convert_boolean_arguments, convert_file_contents, convert_removed_options, arg_to_bool

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
    ('newest', 'only_newest'),
    ('skip', 'skip_content_types'),

    # Not part of the CLI yet; may be removed entirely
    ('remove_old', 'remove_old'),
    ('num_old_packages', 'retain_old_count'),
    ('purge_orphaned', 'remove_orphaned'),
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
    ('generate_metadata', 'regenerate_metadata'),
    ('metadata_types', 'skip_content_types'),
]

VALID_SKIP_TYPES = ['packages', 'distributions', 'errata']

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
        repo_id = kwargs.pop('repo-id')
        description = kwargs.pop('description', None)
        display_name = kwargs.pop('display-name', None)
        auto_publish = kwargs.pop('auto-publish', None)

        if auto_publish:
            auto_publish = arg_to_bool(auto_publish)
            if auto_publish:
                self.context.prompt.render_failure_message(_('Value for auto-publish must be either true or false'))
                return

        try:
            notes = args_to_notes_dict(kwargs, include_none=False)
            importer_config = args_to_importer_config(kwargs)
            distributor_config = args_to_distributor_config(kwargs)
        except InvalidConfig, e:
            self.context.prompt.render_failure_message(e[0])
            return

        # During create (but not update), if the relative path isn't specified
        # it is derived from the feed_url
        if 'relative_url' not in distributor_config:
            if 'feed_url' in importer_config:
                url_parse = urlparse(encode_unicode(importer_config['feed_url']))

                if url_parse[2] in ('', '/'):
                    relative_path = '/' + repo_id
                else:
                    relative_path = url_parse[2]
                distributor_config['relative_url'] = relative_path
            else:
                distributor_config['relative_url'] = repo_id

        # Both http and https must be specified in the distributor config, so
        # make sure they are initiall set here (default to only https)
        if 'http' not in distributor_config and 'https' not in distributor_config:
            distributor_config['https'] = True
            distributor_config['http'] = False

        # Make sure both are referenced
        for k in ('http', 'https'):
            if k not in distributor_config:
                distributor_config[k] = False

        # Likely a temporary hack as we continue to refine how metadata generation
        # is done on the distributor
        distributor_config['generate_metadata'] = True

        # Package distributors for the call
        distributors = [(DISTRIBUTOR_TYPE_ID, distributor_config, True, DISTRIBUTOR_ID)]

        # Create the repository; let exceptions bubble up to the framework exception handler
        self.context.server.repo.create_and_configure(repo_id, display_name, description, notes, IMPORTER_TYPE_ID, importer_config, distributors)

        self.context.prompt.render_success_message('Successfully created repository [%s]' % repo_id)

class YumRepoDeleteCommand(PulpCliCommand):
    def __init__(self, context):
        desc = 'deletes a repository'
        PulpCliCommand.__init__(self, 'delete', desc, self.delete)
        self.context = context

        self.add_option(PulpCliOption('--repo-id', 'identifies the repository to delete', required=True))

    def delete(self, **kwargs):
        repo_id = kwargs['repo-id']
        response = self.context.server.repo.delete(repo_id)

        if not response.is_async():
            self.context.prompt.render_success_message(_('Repository [%(r)s] successfully deleted') % {'r' : repo_id})
        else:
            d = 'Repository delete postponed due to another operation. Progress ' \
                'on this task can be viewed using the commands under "repo tasks".'
            self.context.prompt.render_paragraph(_(d))
            self.context.prompt.render_reasons(response.response_body.reasons)

class YumRepoUpdateCommand(PulpCliCommand):
    def __init__(self, context):
        desc = 'updates an existing repository\'s configuration'
        PulpCliCommand.__init__(self, 'update', desc, self.update)

        self.context = context

        add_repo_options(self, True)

    def update(self, **kwargs):

        # Gather data
        repo_id = kwargs.pop('repo-id')
        description = kwargs.pop('description', None)
        display_name = kwargs.pop('display-name', None)
        auto_publish = kwargs.pop('auto-publish', None)

        if auto_publish:
            auto_publish = arg_to_bool(auto_publish)
            if auto_publish is None:
                self.context.prompt.render_failure_message(_('Value for auto-publish must be either true or false'))
                return

        try:
            notes = args_to_notes_dict(kwargs, include_none=True)
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
                   description, notes, importer_config, distributor_configs)

        if not response.is_async():
            self.context.prompt.render_success_message(_('Repository [%(r)s] successfully updated') % {'r' : repo_id})
        else:
            d = 'Repository update postponed due to another operation. Progress '\
                'on this task can be viewed using the commands under "repo tasks".'
            self.context.prompt.render_paragraph(_(d))
            self.context.prompt.render_reasons(response.response_body.reasons)


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
            filters += ['auto_publish', 'sync_config', 'publish_config']

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
                    r['auto_publish'] = distributors[0]['auto_publish']

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
    basic_group = PulpCliOptionGroup('Basic')
    throttling_group = PulpCliOptionGroup('Throttling')
    ssl_group = PulpCliOptionGroup('Feed Authentication')
    proxy_group = PulpCliOptionGroup('Feed Proxy')
    sync_group = PulpCliOptionGroup('Synchronization')
    publish_group = PulpCliOptionGroup('Publishing')
    repo_auth_group = PulpCliOptionGroup('Client Authentication')

    # Order added indicates order in usage, so pay attention to this order when
    # dorking with it to make sure it makes sense
    command.add_option_group(basic_group)
    command.add_option_group(sync_group)
    command.add_option_group(publish_group)
    command.add_option_group(ssl_group)
    command.add_option_group(repo_auth_group)
    command.add_option_group(proxy_group)
    command.add_option_group(throttling_group)

    # Metadata Options
    basic_group.add_option(PulpCliOption('--repo-id', 'uniquely identifies the repository; only alphanumeric, -, and _ allowed', required=True))
    basic_group.add_option(PulpCliOption('--feed', 'URL of the external source repository to sync', required=False))
    basic_group.add_option(PulpCliOption('--display-name', 'user-readable display name for the repository', required=False))
    basic_group.add_option(PulpCliOption('--description', 'user-readable description of the repo\'s contents', required=False))
    d =  'adds/updates/deletes key-value pairs to programmtically identify the repository; '
    d += 'pairs must be separated by an equal sign (e.g. key=value); multiple notes can '
    d += 'be changed by specifying this option multiple times; notes are deleted by '
    d += 'specifying "" as the value'
    basic_group.add_option(PulpCliOption('--note', d, required=False, allow_multiple=True))
    d =  'if "true", on each successful sync the repository will automatically be ' \
    'published on the configured protocols; if "false" synchronized content will ' \
    'only be available after manually publishing the repository'
    basic_group.add_option(PulpCliOption('--auto-publish', _(d), required=False))

    # Synchronization Options
    sync_group.add_option(PulpCliOption('--only-newest', 'if "true", only the newest version of a given package is downloaded', required=False))
    sync_group.add_option(PulpCliOption('--skip-types', 'comma-separated list of types to synchronize, if omitted all types will be synchronized; valid values are: %s' % ', '.join(VALID_SKIP_TYPES), required=False))
    sync_group.add_option(PulpCliOption('--verify-size', 'if "true", the size of each synchronized file will be verified against the repo metadata; defaults to false', required=False))
    sync_group.add_option(PulpCliOption('--verify-checksum', 'if "true", the checksum of each synchronized file will be verified against the repo metadata; defaults to false', required=False))

    # Proxy Options
    proxy_group.add_option(PulpCliOption('--proxy-url', 'URL to the proxy server to use', required=False))
    proxy_group.add_option(PulpCliOption('--proxy-port', 'port on the proxy server to make requests', required=False))
    proxy_group.add_option(PulpCliOption('--proxy-user', 'username used to authenticate with the proxy server', required=False))
    proxy_group.add_option(PulpCliOption('--proxy-pass', 'password used to authenticate with the proxy server', required=False))

    # Throttling Options
    throttling_group.add_option(PulpCliOption('--max-speed', 'maximum bandwidth used per download thread, in KB/sec, when synchronizing the repo', required=False))
    throttling_group.add_option(PulpCliOption('--num-threads', 'number of threads that will be used to synchronize the repo', required=False))

    # SSL Options
    ssl_group.add_option(PulpCliOption('--feed-ca-cert', 'full path to the CA certificate that should be used to verify the external repo server\'s SSL certificate', required=False))
    ssl_group.add_option(PulpCliOption('--verify-feed-ssl', 'if "true", the feed\'s SSL certificate will be verified against the feed_ca_cert', required=False))
    ssl_group.add_option(PulpCliOption('--feed-cert', 'full path to the certificate to use for authentication when accessing the external feed', required=False))
    ssl_group.add_option(PulpCliOption('--feed-key', 'full path to the private key for feed_cert', required=False))

    # Publish Options
    publish_group.add_option(PulpCliOption('--relative-url', 'relative path the repository will be served from; defaults to relative path of the feed URL', required=False))
    publish_group.add_option(PulpCliOption('--serve-http', 'if "true", the repository will be served over HTTP; defaults to false', required=False))
    publish_group.add_option(PulpCliOption('--serve-https', 'if "true", the repository will be served over HTTPS; defaults to true', required=False))
    publish_group.add_option(PulpCliOption('--checksum-type', 'type of checksum to use during metadata generation', required=False))
    publish_group.add_option(PulpCliOption('--gpg-key', 'GPG key used to sign and verify packages in the repository', required=False))
    publish_group.add_option(PulpCliOption('--regenerate-metadata', 'if "true", when the repository is published the repo metadata will be regenerated instead of reusing the metadata downloaded from the feed', required=False))

    # Publish Security Options
    repo_auth_group.add_option(PulpCliOption('--host-ca', 'full path to the CA certificate that signed the repository hosts\'s SSL certificate when serving over HTTPS', required=False))
    repo_auth_group.add_option(PulpCliOption('--auth-ca', 'full path to the CA certificate that should be used to verify client authentication certificates; setting this turns on client authentication for the repository', required=False))
    repo_auth_group.add_option(PulpCliOption('--auth-cert', 'full path to the entitlement certificate that will be given to bound consumers to grant access to this repository', required=False))

def args_to_notes_dict(kwargs, include_none=True):
    """
    Extracts notes information from the user-specified options and packages
    them up to be sent in either repo create or update.

    @param include_none: if true, keys with a value of none will be included
           in the returned dict; otherwise, only keys with non-none values will
           be present
    @type  include_none: bool

    @return: dict if one or more notes were specified; None otherwise

    @raises InvalidConfig: if one or more of the notes is malformed
    """
    if 'note' not in kwargs or kwargs['note'] is None:
        return None

    result = {}
    for unparsed_note in kwargs['note']:
        pieces = unparsed_note.split('=', 1)

        if len(pieces) < 2:
            raise InvalidConfig(_('Notes must be specified in the format key=value'))

        key = pieces[0]
        value = pieces[1]

        if value in (None, '', '""'):
            value = None

        if value is None and not include_none:
            continue

        result[key] = value

    return result

def args_to_importer_config(kwargs):
    """
    Takes the arguments read from the CLI and converts the client-side input
    to the server-side expectations. The supplied dict will not be modified.

    @return: config to pass into the add/update importer calls
    @raise InvalidConfig: if one or more arguments is not valid for the importer
    """

    importer_config = _prep_config(kwargs, IMPORTER_CONFIG_KEYS)

    # Parsing of true/false
    boolean_arguments = ('ssl_verify', 'verify_size', 'verify_checksum', 'newest')
    convert_boolean_arguments(boolean_arguments, importer_config)

    # Read in the contents of any files that were specified
    file_arguments = ('ssl_ca_cert', 'ssl_client_cert', 'ssl_client_key')
    convert_file_contents(file_arguments, importer_config)

    # Handle skip types
    if 'skip' in importer_config:
        skip_as_list = _convert_skip_types(importer_config['skip'])
        importer_config['skip'] = skip_as_list

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
    boolean_arguments = ('http', 'https', 'generate_metadata')
    convert_boolean_arguments(boolean_arguments, distributor_config)

    # Read in the contents of any files that were specified
    file_arguments = ('auth_cert', 'auth_ca', 'https_ca', 'gpgkey')
    convert_file_contents(file_arguments, distributor_config)

    # Handle skip types
    if 'metadata_types' in distributor_config:
        skip_as_list = _convert_skip_types(distributor_config['metadata_types'])
        distributor_config['metadata_types'] = skip_as_list

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

    # User-specified flags use hyphens but the importer/distributor want
    # underscores, so do a quick translation here before anything else.
    for k in kwargs.keys():
        v = kwargs.pop(k)
        new_key = k.replace('-', '_')
        kwargs[new_key] = v

    # Populate the plugin config with the plugin-relevant keys in the user args
    user_arg_keys = [k[1] for k in plugin_config_keys]
    plugin_config = dict([(k, v) for k, v in kwargs.items() if k in user_arg_keys])

    # Simple name translations
    for plugin_key, cli_key in plugin_config_keys:
        plugin_config[plugin_key] = plugin_config.pop(cli_key, None)

    # Apply option removal conventions
    convert_removed_options(plugin_config)

    return plugin_config

def _convert_skip_types(skip_types):
    """
    Parses the skip_types parameter and converts the comma-separated list
    into a python list.
    """

    parsed = skip_types.split(',')
    parsed = [p.strip() for p in parsed]

    unmatched = [p for p in parsed if p not in VALID_SKIP_TYPES]
    if len(unmatched) > 0:
        raise InvalidConfig(_('Types must be a comma-separated list using only the following values: %s' % ', '.join(VALID_SKIP_TYPES)))

    return parsed

