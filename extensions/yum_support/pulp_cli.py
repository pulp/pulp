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

import sys

from pulp.gc_client.framework.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag, PulpCliOptionGroup
from pulp.gc_client.api.exceptions import RequestException, DuplicateResourceException, BadRequestException

IMPORTER_TYPE_ID = 'yum_importer'

def initialize(context):

    if not context.extension_config.getboolean('main', 'enabled'):
        return

    # Remove generic commands/sections that we want to override
    repo_section = context.cli.find_section('repo')
    repo_section.remove_command('create')
    repo_section.remove_command('update')
    repo_section.remove_subsection('importer')

    # Add in overridden yum functionality
    repo_section.add_command(YumRepoCreateCommand(context))

def create_repo_options(command, is_update):
    """
    Adds options/flags for all repo configuration values (repo, importer, and
    distributor). This is meant to be called for both create and update commands
    to simplify consistency

    @param command: command to add options to
    """

    # Groups
    required_group = PulpCliOptionGroup('Required')
    d = '(optional) user-readable information about the repository'
    if is_update: d += '; specify "" to remove any of these values'
    metadata_group = PulpCliOptionGroup('Metadata', d)

    throttling_group = PulpCliOptionGroup('Throttling', '(optional) controls the bandwidth and CPU usage when synchronizing this repo')
    ssl_group = PulpCliOptionGroup('Security', '(optional) credentials and configuration for synchronizing secured external repositories')
    verify_group = PulpCliOptionGroup('Verification', '(optional) controls the amount of verification on synchronized data')
    proxy_group = PulpCliOptionGroup('Proxy', '(optional) configures synchronization to go through a proxy server')

    # Order added indicates order in usage, so pay attention to this order when
    # dorking with it to make sure it makes sense
    command.add_option_group(required_group)
    command.add_option_group(metadata_group)
    command.add_option_group(verify_group)
    command.add_option_group(ssl_group)
    command.add_option_group(proxy_group)
    command.add_option_group(throttling_group)

    # Required Options
    required_group.add_option(PulpCliOption('--id', 'uniquely identifies the repository; only alphanumeric, -, and _ allowed', required=True))
    required_group.add_option(PulpCliOption('--feed_url', 'URL of the external source repository to sync', required=True))

    # Metadata Options
    metadata_group.add_option(PulpCliOption('--display_name', 'user-readable display name for the repository', required=False))
    metadata_group.add_option(PulpCliOption('--description', 'user-readable description of the repo\'s contents', required=False))

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

def args_to_importer_config(kwargs):
    """
    Takes the arguments read from the CLI and converts the client-side input
    to the server-side expectations. The supplied dict will not be modified.

    @return: config to pass into the add/update importer calls
    """

    importer_config = dict(kwargs)

    # Simple name translations
    translations = [
        ('ssl_ca_cert', 'feed_ca_cert'),
        ('ssl_client_cert', 'feed_cert'),
        ('ssl_client_key', 'feed_key'),
        ('ssl_verify', 'verify_feed_ssl'),
    ]
    for t, o in translations:
        importer_config[t] = importer_config.pop(o, None)

    # Verify options is expected as a dict, so repackage those now
    importer_config['verify_options'] = {
        'size' : importer_config.pop('verify_size', None),
        'checksum' : importer_config.pop('verify_checksum', None),
    }

    # Strip out anything with a None value. The importer won't barf at this,
    # but Pulp will store them in the config as key : None. This tends to
    # make the output of viewing the importer config kinda ugly, so let's try
    # this approach and see how it turns out.

    importer_config = dict([(k, v) for k, v in importer_config.items() if v is not None])

    # Special None stripping for verify_options since it's a dict
    popped = 0
    if importer_config['verify_options']['size'] is None:
        importer_config['verify_options'].pop('size')
        popped += 1

    if importer_config['verify_options']['checksum'] is None:
        importer_config['verify_options'].pop('checksum')
        popped += 1

    if popped == 2:
        importer_config.pop('verify_options') # Nothing in here, so remove it too

    return importer_config

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

        repo_id = kwargs.pop('id') # pop it out so it's not part of importer config
        description = kwargs.pop('description', None)
        display_name = kwargs.pop('display_name', None)

        # TODO: split apart the remaining arguments between importer and distributor config
        importer_config = args_to_importer_config(kwargs)

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