# Copyright (c) 2012 Red Hat, Inc.
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
import logging
from urlparse import urlparse

from pulp.client.arg_utils import (InvalidConfig, convert_file_contents,
                                   convert_removed_options)
from pulp.client.commands.criteria import CriteriaCommand
from pulp.client.commands.repo.cudl import (CreateRepositoryCommand, ListRepositoriesCommand,
                                            UpdateRepositoryCommand)
from pulp.client.commands import options as std_options
from pulp.common.util import encode_unicode

from pulp_rpm.common import constants, ids
from pulp_rpm.extension.admin import repo_options

# -- constants ----------------------------------------------------------------

DESC_SEARCH = _('searches for RPM repositories on the server')

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
    ('skip', 'skip'),
    ('remove_old', 'remove_old'),
    ('num_old_packages', 'retain_old_count'),
]

YUM_DISTRIBUTOR_CONFIG_KEYS = [
    ('relative_url', 'relative_url'),
    ('http', 'serve_http'),
    ('https', 'serve_https'),
    ('gpgkey', 'gpg_key'),
    ('checksum_type', 'checksum_type'),
    ('auth_ca', 'auth_ca'),
    ('auth_cert', 'auth_cert'),
    ('https_ca', 'host_ca'),
    ('generate_metadata', 'regenerate_metadata'),
    ('skip', 'skip'),
]

ISO_DISTRIBUTOR_CONFIG_KEYS = [
    ('http', 'serve_http'),
    ('https', 'serve_https'),
    ('https_ca', 'host_ca'),
    ('skip', 'skip'),
]

LOG = logging.getLogger(__name__)


class RpmRepoCreateCommand(CreateRepositoryCommand):

    def __init__(self, context):
        super(RpmRepoCreateCommand, self).__init__(context)

        # The built-in options will be reorganized under a group to keep the
        # help text from being unwieldly. The base class will add them by
        # default, so remove them here before they are readded under a group.
        self.options = []

        repo_options.add_to_command(self)

    def run(self, **kwargs):

        # Gather data
        repo_id = kwargs.pop(std_options.OPTION_REPO_ID.keyword)
        description = kwargs.pop(std_options.OPTION_DESCRIPTION.keyword, None)
        display_name = kwargs.pop(std_options.OPTION_NAME.keyword, None)
        notes = kwargs.pop(std_options.OPTION_NOTES.keyword) or {}

        # Add a note to indicate this is a Puppet repository
        notes[constants.REPO_NOTE_KEY] = constants.REPO_NOTE_RPM

        try:
            importer_config = args_to_importer_config(kwargs)
            yum_distributor_config = args_to_yum_distributor_config(kwargs)
            iso_distributor_config = args_to_iso_distributor_config(kwargs)
        except InvalidConfig, e:
            self.prompt.render_failure_message(str(e))
            return

        # During create (but not update), if the relative path isn't specified
        # it is derived from the feed_url
        if 'relative_url' not in yum_distributor_config:
            if 'feed_url' in importer_config:
                url_parse = urlparse(encode_unicode(importer_config['feed_url']))

                if url_parse[2] in ('', '/'):
                    relative_path = '/' + repo_id
                else:
                    relative_path = url_parse[2]
                yum_distributor_config['relative_url'] = relative_path
            else:
                yum_distributor_config['relative_url'] = repo_id

        # Both http and https must be specified in the distributor config, so
        # make sure they are initially set here (default to only https)
        if 'http' not in yum_distributor_config and 'https' not in yum_distributor_config:
            yum_distributor_config['https'] = True
            yum_distributor_config['http'] = False

        # Make sure both are referenced
        for k in ('http', 'https'):
            if k not in yum_distributor_config:
                yum_distributor_config[k] = False

        # Ensure default values for http and https for iso_distributor
        # if they are not set
        if 'http' not in iso_distributor_config and 'https' not in iso_distributor_config:
            iso_distributor_config['https'] = True
            iso_distributor_config['http'] = False

        # Make sure both are referenced
        for k in ('http', 'https'):
            if k not in iso_distributor_config:
                iso_distributor_config[k] = False

        # Package distributors for the call
        distributors = [
            dict(distributor_type=ids.TYPE_ID_DISTRIBUTOR_YUM, distributor_config=yum_distributor_config,
                 auto_publish=True, distributor_id=ids.YUM_DISTRIBUTOR_ID),
            dict(distributor_type=ids.TYPE_ID_DISTRIBUTOR_ISO, distributor_config=iso_distributor_config,
                 auto_publish=False, distributor_id=ids.ISO_DISTRIBUTOR_ID)
        ]

        # Create the repository; let exceptions bubble up to the framework exception handler
        self.context.server.repo.create_and_configure(
            repo_id, display_name, description, notes,
            ids.TYPE_ID_IMPORTER_YUM, importer_config, distributors
        )

        msg = _('Successfully created repository [%(r)s]')
        self.prompt.render_success_message(msg % {'r' : repo_id})


class RpmRepoUpdateCommand(UpdateRepositoryCommand):

    def __init__(self, context):
        super(RpmRepoUpdateCommand, self).__init__(context)

        # The built-in options will be reorganized under a group to keep the
        # help text from being unwieldly. The base class will add them by
        # default, so remove them here before they are readded under a group.
        self.options = []

        repo_options.add_to_command(self)

    def run(self, **kwargs):

        # Gather data
        repo_id = kwargs.pop(std_options.OPTION_REPO_ID.keyword)
        description = kwargs.pop(std_options.OPTION_DESCRIPTION.keyword, None)
        display_name = kwargs.pop(std_options.OPTION_NAME.keyword, None)
        notes = kwargs.pop(std_options.OPTION_NOTES.keyword, None)

        try:
            importer_config = args_to_importer_config(kwargs)
        except InvalidConfig, e:
            self.prompt.render_failure_message(str(e))
            return

        try:
            yum_distributor_config = args_to_yum_distributor_config(kwargs)
        except InvalidConfig, e:
            self.prompt.render_failure_message(str(e))
            return

        try:
            iso_distributor_config = args_to_iso_distributor_config(kwargs)
        except InvalidConfig, e:
            self.prompt.render_failure_message(str(e))
            return

        distributor_configs = {ids.TYPE_ID_DISTRIBUTOR_YUM : yum_distributor_config,
                               ids.TYPE_ID_DISTRIBUTOR_ISO : iso_distributor_config}

        response = self.context.server.repo.update_repo_and_plugins(
            repo_id, display_name, description, notes,
            importer_config, distributor_configs
        )

        if not response.is_async():
            msg = _('Repository [%(r)s] successfully updated')
            self.prompt.render_success_message(msg % {'r' : repo_id})
        else:
            msg = _('Repository update postponed due to another operation. '
                    'Progress on this task can be viewed using the commands '
                    'under "repo tasks"')
            self.prompt.render_paragraph(msg)
            self.prompt.render_reasons(response.response_body.reasons)


class RpmRepoListCommand(ListRepositoriesCommand):

    def __init__(self, context):
        super(RpmRepoListCommand, self).__init__(context)

    def get_repositories(self, query_params, **kwargs):
        all_repos = super(RpmRepoListCommand, self).get_repositories(query_params, **kwargs)

        rpm_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if constants.REPO_NOTE_KEY in notes and notes[constants.REPO_NOTE_KEY] == constants.REPO_NOTE_RPM:
                rpm_repos.append(repo)

        return rpm_repos


class RpmRepoSearchCommand(CriteriaCommand):

    def __init__(self, context):
        super(RpmRepoSearchCommand, self).__init__(self.run, name='search',
                                                   description=DESC_SEARCH,
                                                   include_search=True)

        self.context = context
        self.prompt = context.prompt

    def run(self, **kwargs):
        self.prompt.render_title(_('Repositories'))

        # Limit to only RPM repositories
        if kwargs.get('str-eq', None) is None:
            kwargs['str-eq'] = []
        kwargs['str-eq'].append(['notes.%s' % constants.REPO_NOTE_KEY, constants.REPO_NOTE_RPM])

        # Server call
        repo_list = self.context.server.repo_search.search(**kwargs)

        # Display the results
        order = ['id', 'display_name', 'description']
        self.prompt.render_document_list(repo_list, order=order)

# -- utilities ----------------------------------------------------------------

def args_to_importer_config(kwargs):
    """
    Takes the arguments read from the CLI and converts the client-side input
    to the server-side expectations. The supplied dict will not be modified.

    @return: config to pass into the add/update importer calls
    @raise InvalidConfig: if one or more arguments is not valid for the importer
    """

    importer_config = _prep_config(kwargs, IMPORTER_CONFIG_KEYS)

    # Read in the contents of any files that were specified
    file_arguments = ('ssl_ca_cert', 'ssl_client_cert', 'ssl_client_key')
    convert_file_contents(file_arguments, importer_config)

    if 'num_old_packages' in importer_config:
        if importer_config['num_old_packages'] is None:
            importer_config['num_old_packages'] = 0
        else:
            importer_config['num_old_packages'] = int(importer_config['num_old_packages'])
    LOG.debug('Importer configuration options')
    LOG.debug(importer_config)
    return importer_config


def args_to_yum_distributor_config(kwargs):
    """
    Takes the arguments read from the CLI and converts the client-side input
    to the server-side expectations. The supplied dict will not be modified.

    @return: config to pass into the add/update distributor calls
    @raise InvalidConfig: if one or more arguments is not valid for the distributor
    """
    distributor_config = _prep_config(kwargs, YUM_DISTRIBUTOR_CONFIG_KEYS)

    # Read in the contents of any files that were specified
    file_arguments = ('auth_cert', 'auth_ca', 'https_ca', 'gpgkey')
    convert_file_contents(file_arguments, distributor_config)

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


def args_to_iso_distributor_config(kwargs):
    """
    Takes the arguments read from the CLI and converts the client-side input
    to the server-side expectations. The supplied dict will not be modified.

    @return: config to pass into the add/update distributor calls
    @raise InvalidConfig: if one or more arguments is not valid for the distributor
    """
    distributor_config = _prep_config(kwargs, ISO_DISTRIBUTOR_CONFIG_KEYS)

    # Read in the contents of any files that were specified
    file_arguments = ('https_ca',)
    convert_file_contents(file_arguments, distributor_config)

    LOG.debug('ISO Distributor configuration options')
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
