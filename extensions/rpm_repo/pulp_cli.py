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
import sys

from pulp.gc_client.framework.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag, PulpCliOptionGroup
from pulp.gc_client.api.exceptions import RequestException, DuplicateResourceException, BadRequestException

# -- constants ----------------------------------------------------------------

IMPORTER_TYPE_ID = 'yum_importer'

# Tuples of importer key name to more user-friendly CLI name
IMPORTER_KEY_TRANSLATIONS = [
    ('ssl_ca_cert', 'feed_ca_cert'),
    ('ssl_client_cert', 'feed_cert'),
    ('ssl_client_key', 'feed_key'),
    ('ssl_verify', 'verify_feed_ssl'),
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
    repo_section.remove_subsection('importer')

    # Add in overridden yum functionality
    repo_section.add_command(YumRepoCreateCommand(context))
    repo_section.add_command(YumRepoUpdateCommand(context))
    repo_section.add_command(YumRepoListCommand(context))

# -- command implementations --------------------------------------------------

class YumRepoCreateCommand(PulpCliCommand):
    def __init__(self, context):
        desc = 'creates a new repository that is configured to sync and publish RPM related content'
        PulpCliCommand.__init__(self, 'create', desc, self.create)

        self.context = context

        create_repo_options(self, False)

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
        except InvalidConfig, e:
            self.context.prompt.render_failure_message(e[0])
            return

        # TODO: This whole mess of exception stuff is gonna be handled by the exception handler

        # Create the repository
        try:
            self.context.server.repo.create(repo_id, display_name, description, None)
        except DuplicateResourceException:
            self.context.prompt.render_failure_message('Repository already exists with ID [%s]' % repo_id)
            return
        except BadRequestException:
            self.context.logger.exception('Invalid data during repository [%s] creation' % repo_id)
            self.context.prompt.render_failure_message('Repository metadata (id, display_name, description) was invalid')
            return
        except RequestException, e:
            self.context.logger.exception('Error creating repository [%s]' % repo_id)
            self.context.prompt.render_failure_message('Error creating repository [%s]' % repo_id)
            raise e, None, sys.exc_info()[2]

        # Add the importer
        try:
            self.context.server.repo_importer.create(repo_id, IMPORTER_TYPE_ID, importer_config)
        except BadRequestException:
            self.context.logger.exception('Invalid data during importer addition to repository [%s]' % repo_id)
            self.context.prompt.render_failure_message('Error during importer configuration of repository [%s]' % repo_id)
            return
        except RequestException, e:
            self.context.logger.exception('Error adding importer')
            self.context.prompt.render_failure_message('Error configuring importer for repository [%s]' % repo_id)
            raise e, None, sys.exc_info()[2]

        self.context.prompt.render_success_message('Successfully created repository [%s]' % repo_id)


class YumRepoUpdateCommand(PulpCliCommand):
    def __init__(self, context):
        desc = 'updates an existing repository\'s configuration'
        PulpCliCommand.__init__(self, 'update', desc, self.update)

        self.context = context

        create_repo_options(self, True)

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

        something_changed = False

        # Update the repo itself if necessary
        if description is not None or display_name is not None:
            delta = {}
            if description is not None: delta['description'] = description
            if display_name is not None: delta['display_name'] = display_name

            self.context.server.repo.update(repo_id, delta)
            something_changed = True

        # Update the importer config if necessary
        if len(importer_config) > 0:
            self.context.server.repo_importer.update(repo_id, IMPORTER_TYPE_ID, importer_config)
            something_changed = True

        if something_changed:
            self.context.prompt.render_success_message('Repository [%s] successfully updated' % repo_id)
        else:
            self.context.prompt.write('No changes specified for repository [%s]' % repo_id)

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
        order = filters

        # Process each repository to clean up/restructure various data
        for r in repo_list:

            # Pull the importer/distributor configs into the repo itself. For now
            # assume one of each since in the RPM commands we lock the user into
            # that. We may have to revisit the distributor part in the future.
            importers = r.pop('importers', None)
            distributors = r.pop('distributors', None)
            if show_details:

                if importers is not None and len(importers) > 0:
                    r['sync_config'] = importers[0]['config']
                    filters += ['sync_config']

                    # Translate the importer config keys to cli counterparts
                    for importer_key, cli_key in IMPORTER_KEY_TRANSLATIONS:
                        if importer_key in r['sync_config']:
                            r['sync_config'][cli_key] = r['sync_config'].pop(importer_key)

                    # Certificates are too long to display, so simply indicate if they
                    # are present. Eventually we can add a flag that will show them.
                    for key in ('feed_ca_cert', 'feed_cert', 'feed_key'):
                        if key in r['sync_config']:
                            r['sync_config'][key] = _('Yes')

                if distributors is not None and len(distributors) > 0:
                    r['publish_config'] = distributors[0]['config']
                    filters += ['publish_config']

            # We don't want to display the proxy password in plain text, so
            # if it's present swap it out with astericks
            if 'proxy_pass' in r:
                r['proxy_pass'] = '*' * len(r['proxy_pass'])


        self.prompt.render_document_list(repo_list, filters=filters, order=order)

# -- parsing utilities --------------------------------------------------------

def create_repo_options(command, is_update):
    """
    Adds options/flags for all repo configuration values (repo, importer, and
    distributor). This is meant to be called for both create and update commands
    to simplify consistency

    @param command: command to add options to
    """

    def munge_description(d):
        if is_update: d += '; specify "" to remove any of these values'
        return d

    # Groups
    required_group = PulpCliOptionGroup('Required')

    d = munge_description('(optional) basic information about the repository')
    basic_group = PulpCliOptionGroup('Basic', d)

    d = munge_description('(optional) controls the bandwidth and CPU usage when synchronizing this repo')
    throttling_group = PulpCliOptionGroup('Throttling', d)

    d = munge_description('(optional) credentials and configuration for synchronizing secured external repositories')
    ssl_group = PulpCliOptionGroup('Security', d)

    verify_group = PulpCliOptionGroup('Verification', '(optional) controls the amount of verification on synchronized data')

    d = munge_description('(optional) configures synchronization to go through a proxy server')
    proxy_group = PulpCliOptionGroup('Proxy', d)

    # Order added indicates order in usage, so pay attention to this order when
    # dorking with it to make sure it makes sense
    command.add_option_group(required_group)
    command.add_option_group(basic_group)
    command.add_option_group(verify_group)
    command.add_option_group(ssl_group)
    command.add_option_group(proxy_group)
    command.add_option_group(throttling_group)

    # Required Options
    required_group.add_option(PulpCliOption('--id', 'uniquely identifies the repository; only alphanumeric, -, and _ allowed', required=True))

    # Feed URL is special: required for create, optional for update

    if not is_update:
        feed_url_dest = required_group
    else:
        feed_url_dest = basic_group

    feed_url_dest.add_option(PulpCliOption('--feed_url', 'URL of the external source repository to sync', required=not is_update))

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

class InvalidConfig(Exception): pass

def args_to_importer_config(kwargs):
    """
    Takes the arguments read from the CLI and converts the client-side input
    to the server-side expectations. The supplied dict will not be modified.

    @return: config to pass into the add/update importer calls
    """

    importer_config = dict(kwargs)

    # Simple name translations
    for importer_key, cli_key in IMPORTER_KEY_TRANSLATIONS:
        importer_config[importer_key] = importer_config.pop(cli_key, None)

    # Strip out anything with a None value. The way the parser works, all of
    # the possible options will be present with None as the value. Strip out
    # everything with a None value now as it means it hasn't been specified
    # by the user (removals are done by specifying ''.
    importer_config = dict([(k, v) for k, v in importer_config.items() if v is not None])

    # Now convert any "" strings into None. This should be safe in all cases and
    # is the mechanic used to get "remove config option" semantics.
    convert_keys = [k for k in importer_config if importer_config[k] == '']
    for k in convert_keys:
        importer_config[k] = None

    # Parsing of true/false
    flag_arguments = ('ssl_verify', 'verify_size', 'verify_checksum')
    for f in flag_arguments:
        if f in importer_config:
            if f not in importer_config or importer_config[f] is None:
                continue
            v = importer_config.pop(f)
            if v.strip().lower() == 'true':
                importer_config[f] = True
                continue
            if v.strip().lower() == 'false':
                importer_config[f] = False
                continue
            raise InvalidConfig('Value for %s must be either true or false' % f)

    # Read in the contents of any files that were specified
    file_arguments = ('ssl_ca_cert', 'ssl_client_cert', 'ssl_client_key')
    for arg in file_arguments:
        if arg in importer_config and importer_config[arg] is not None:
            contents = read_file(importer_config[arg])
            importer_config[arg] = contents

    LOG.debug('Importer configuration options')
    LOG.debug(importer_config)

    return importer_config

def read_file(filename):
    """
    Utility for reading a file specified as a command argument, raising
    InvalidConfiguration if the file cannot be read.

    @return: contents of the file
    """

    try:
        f = open(filename)
        contents = f.read()
        f.close()

        return contents
    except:
        raise InvalidConfig('File [%s] cannot be read' % filename)