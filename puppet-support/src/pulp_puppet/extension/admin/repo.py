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

from pulp.client.commands.criteria import CriteriaCommand
from pulp.client import arg_utils
from pulp.client.commands.repo.cudl import CreateRepositoryCommand, ListRepositoriesCommand, UpdateRepositoryCommand
from pulp.client.commands import options
from pulp.client.extensions.extensions import PulpCliOption

from pulp_puppet.common import constants

# -- constants ----------------------------------------------------------------

DESC_FEED = _('URL of the external source from which to import Puppet modules')
OPTION_FEED = PulpCliOption('--feed', DESC_FEED, required=False)

DESC_QUERY = _(
    'query to issue against the feed\'s modules.json file to scope which '
    'modules are imported; multiple queries may be added by specifying this '
    'argument multiple times'
)
OPTION_QUERY = PulpCliOption('--query', DESC_QUERY, required=False, allow_multiple=True)

DESC_HTTP = _('if "true", the repository will be served over HTTP; defaults to true')
OPTION_HTTP = PulpCliOption('--serve-http', DESC_HTTP, required=False)

DESC_HTTPS = _('if "true", the repository will be served over HTTPS; defaults to false')
OPTION_HTTPS = PulpCliOption('--serve-https', DESC_HTTPS, required=False)

DESC_SEARCH = _('searches for Puppet repositories on the server')

# -- commands -----------------------------------------------------------------

class CreatePuppetRepositoryCommand(CreateRepositoryCommand):

    def __init__(self, context):
        super(CreatePuppetRepositoryCommand, self).__init__(context)

        self.add_option(OPTION_FEED)
        self.add_option(OPTION_QUERY)
        self.add_option(OPTION_HTTP)
        self.add_option(OPTION_HTTPS)

    def run(self, **kwargs):

        # -- repository metadata --
        repo_id = kwargs[options.OPTION_REPO_ID.keyword]
        description = kwargs[options.OPTION_DESCRIPTION.keyword]
        notes = kwargs.pop(options.OPTION_NOTES.keyword) or {}

        # Add a note to indicate this is a Puppet repository
        notes[constants.REPO_NOTE_KEY] = constants.REPO_NOTE_PUPPET

        name = repo_id
        if options.OPTION_NAME.keyword in kwargs:
            name = kwargs[options.OPTION_NAME.keyword]

        # -- importer metadata --
        importer_config = {
            constants.CONFIG_FEED : kwargs[OPTION_FEED.keyword],
            constants.CONFIG_QUERIES : kwargs[OPTION_QUERY.keyword],
        }
        arg_utils.convert_removed_options(importer_config)

        # -- distributor metadata --
        distributor_config = {
            constants.CONFIG_SERVE_HTTP : kwargs[OPTION_HTTP.keyword],
            constants.CONFIG_SERVE_HTTPS : kwargs[OPTION_HTTPS.keyword],
        }
        arg_utils.convert_removed_options(distributor_config)
        arg_utils.convert_boolean_arguments((constants.CONFIG_SERVE_HTTP, constants.CONFIG_SERVE_HTTPS), distributor_config)

        distributors = [(constants.DISTRIBUTOR_TYPE_ID, distributor_config, True, constants.DISTRIBUTOR_ID)]

        # Create the repository
        self.context.server.repo.create_and_configure(repo_id, name, description,
            notes, constants.IMPORTER_TYPE_ID, importer_config, distributors)

        msg = _('Successfully created repository [%(r)s]')
        self.context.prompt.render_success_message(msg % {'r' : repo_id})


class UpdatePuppetRepositoryCommand(UpdateRepositoryCommand):

    def __init__(self, context):
        super(UpdatePuppetRepositoryCommand, self).__init__(context)

        self.add_option(OPTION_FEED)
        self.add_option(OPTION_QUERY)
        self.add_option(OPTION_HTTP)
        self.add_option(OPTION_HTTPS)

    def run(self, **kwargs):
        # -- repository metadata --
        repo_id = kwargs.pop(options.OPTION_REPO_ID.keyword)
        description = kwargs.pop(options.OPTION_DESCRIPTION.keyword, None)
        name = kwargs.pop(options.OPTION_NAME.keyword, None)
        notes = kwargs.pop(options.OPTION_NOTES.keyword, None)

        # -- importer metadata --
        importer_config = {
            constants.CONFIG_FEED : kwargs.pop(OPTION_FEED.keyword, None),
            constants.CONFIG_QUERIES : kwargs.pop(OPTION_QUERY.keyword, None),
        }
        arg_utils.convert_removed_options(importer_config)

        # -- distributor metadata --
        distributor_config = {
            constants.CONFIG_SERVE_HTTP : kwargs.pop(OPTION_HTTP.keyword, None),
            constants.CONFIG_SERVE_HTTPS : kwargs.pop(OPTION_HTTPS.keyword, None),
        }
        arg_utils.convert_removed_options(distributor_config)
        arg_utils.convert_boolean_arguments((constants.CONFIG_SERVE_HTTP, constants.CONFIG_SERVE_HTTPS), distributor_config)

        distributor_configs = {constants.DISTRIBUTOR_ID : distributor_config}

        # -- server update --
        response = self.context.server.repo.update_repo_and_plugins(repo_id, name,
                        description, notes, importer_config, distributor_configs)

        if not response.is_async():
            msg = _('Repository [%(r)s] successfully updated')
            self.context.prompt.render_success_message(msg % {'r' : repo_id})
        else:
            d = _('Repository update postponed due to another operation. Progress '
                'on this task can be viewed using the commands under "repo tasks".')
            self.context.prompt.render_paragraph(d, tag='postponed')
            self.context.prompt.render_reasons(response.response_body.reasons)


class ListPuppetRepositoriesCommand(ListRepositoriesCommand):

    def get_repositories(self, query_params, **kwargs):
        all_repos = super(ListPuppetRepositoriesCommand, self).get_repositories(
                          query_params, **kwargs)

        puppet_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if constants.REPO_NOTE_KEY in notes and notes[constants.REPO_NOTE_KEY] == constants.REPO_NOTE_PUPPET:
                puppet_repos.append(repo)

        return puppet_repos


class SearchPuppetRepositoriesCommand(CriteriaCommand):

    def __init__(self, context):
        super(SearchPuppetRepositoriesCommand, self).__init__(
            self.run, name='search', description=DESC_SEARCH,
            include_search=True)

        self.context = context
        self.prompt = context.prompt

    def run(self, **kwargs):
        self.prompt.render_title(_('Repositories'))

        # Limit to only Puppet repositories
        if kwargs.get('str-eq', None) is None:
            kwargs['str-eq'] = []
        kwargs['str-eq'].append(['notes.%s' % constants.REPO_NOTE_KEY, constants.REPO_NOTE_PUPPET])

        # Server call
        repo_list = self.context.server.repo_search.search(**kwargs)

        # Display the results
        order = ['id', 'display_name', 'description']
        self.prompt.render_document_list(repo_list, order=order)
