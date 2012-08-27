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
Contains reusable, expandable commands for the lifecycle and listing of
repositories.

Customization of the commands in this module can be done either by specifying
a method to the command's constructor or by subclassing and overriding the
``run(self, **kwargs)`` method.

Subclasses should be sure to call the super class constructor to ensure the
default options to the command are added. The subclass can then add any
additional options as necessary for its custom behavior.
"""

from gettext import gettext as _

from pulp.bindings.exceptions import NotFoundException
from pulp.client import arg_utils
from pulp.client.commands.options import OPTION_NAME, OPTION_DESCRIPTION, OPTION_NOTES, OPTION_REPO_ID
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliFlag, PulpCliOption

# -- constants ----------------------------------------------------------------

# Command Descriptions
DESC_CREATE = _('creates a new repository')
DESC_UPDATE = _('changes metadata on an existing repository')
DESC_DELETE = _('deletes a repository')
DESC_LIST = _('lists repositories on the Pulp server')

# -- commands -----------------------------------------------------------------

class CreateRepositoryCommand(PulpCliCommand):
    """
    Creates a new repository in Pulp without any importers/distributors assigned.
    """

    def __init__(self, context, name='create', description=DESC_CREATE, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(CreateRepositoryCommand, self).__init__(name, description, method)

        self.add_option(OPTION_REPO_ID)
        self.add_option(OPTION_NAME)
        self.add_option(OPTION_DESCRIPTION)
        self.add_option(OPTION_NOTES)

    def run(self, **kwargs):
        # Collect input
        id = kwargs[OPTION_REPO_ID.keyword]
        name = id
        if OPTION_NAME.keyword in kwargs:
            name = kwargs[OPTION_NAME.keyword]
        description = kwargs[OPTION_DESCRIPTION.keyword]
        notes = arg_utils.args_to_notes_dict(kwargs[OPTION_NOTES.keyword], include_none=True)

        # Call the server
        self.context.server.repo.create(id, name, description, notes)
        msg = _('Repository [%(r)s] successfully created')
        self.prompt.render_success_message(msg % {'r' : id})


class DeleteRepositoryCommand(PulpCliCommand):
    """
    Deletes a repository from the Pulp server.
    """

    def __init__(self, context, name='delete', description=DESC_DELETE, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(DeleteRepositoryCommand, self).__init__(name, description, method)

        self.add_option(OPTION_REPO_ID)

    def run(self, **kwargs):
        id = kwargs[OPTION_REPO_ID.keyword]

        try:
            self.context.server.repo.delete(id)
            msg = _('Repository [%(r)s] successfully deleted')
            self.prompt.render_success_message(msg % {'r' : id})
        except NotFoundException:
            msg = _('Repository [%(r)s] does not exist on the server')
            self.prompt.write(msg % {'r' : id}, tag='not-found')


class UpdateRepositoryCommand(PulpCliCommand):
    """
    Updates the metadata about just a repository, not its importers/distributors.
    """

    def __init__(self, context, name='update', description=DESC_UPDATE, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(UpdateRepositoryCommand, self).__init__(name, description, method)

        self.add_option(OPTION_REPO_ID)
        self.add_option(OPTION_NAME)
        self.add_option(OPTION_DESCRIPTION)
        self.add_option(OPTION_NOTES)

    def run(self, **kwargs):
        # Assemble the delta for all options that were passed in
        delta = dict([(k, v) for k, v in kwargs.items() if v is not None])
        delta.pop(OPTION_REPO_ID.keyword) # not needed in the delta

        # Translate the argument to key name
        if delta.pop(OPTION_NAME.keyword, None) is not None:
            delta['display_name'] = kwargs[OPTION_NAME.keyword]

        if delta.pop(OPTION_NOTES.keyword, None) is not None:
            delta['notes'] = arg_utils.args_to_notes_dict(kwargs[OPTION_NOTES.keyword], include_none=True)

        try:
            self.context.server.repo.update(kwargs[OPTION_REPO_ID.keyword], delta)
            msg = _('Repository [%(r)s] successfully updated')
            self.prompt.render_success_message(msg % {'r' : kwargs[OPTION_REPO_ID.keyword]})
        except NotFoundException:
            msg = _('Repository [%(r)s] does not exist on the server')
            self.prompt.write(msg % {'r' : kwargs[OPTION_REPO_ID.keyword]}, tag='not-found')


class ListRepositoriesCommand(PulpCliCommand):
    """
    Lists all repositories in the Pulp server.
    """

    def __init__(self, context, name='list', description=DESC_LIST, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(ListRepositoriesCommand, self).__init__(name, description, method)

        self.add_option(PulpCliFlag('--summary', _('if specified, only a minimal amount of repository information is displayed')))
        self.add_option(PulpCliOption('--fields', _('comma-separated list of repository fields; if specified, only the given fields will displayed'), required=False))
        self.add_option(PulpCliFlag('--importers', _('if specified, importer configuration is displayed')))
        self.add_option(PulpCliFlag('--distributors', _('if specified, the list of distributors and their configuration is displayed')))

    def run(self, **kwargs):
        self.prompt.render_title(_('Repositories'))

        # Default flags to render_document_list
        filters = ['id', 'display_name', 'description', 'content_unit_count']
        order = filters

        if kwargs['summary'] is True:
            filters = ['id', 'display_name']
            order = filters
        elif kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'id' not in filters:
                filters.append('id')
            order = ['id']

        query_params = {}

        for param in ('importers', 'distributors'):
            if kwargs.get(param):
                query_params[param] = True
                filters.append(param)

        repo_list = self.get_repositories(query_params, **kwargs)
        self.prompt.render_document_list(repo_list, filters=filters, order=order)

    def get_repositories(self, query_params, **kwargs):
        repo_list = self.context.server.repo.repositories(query_params).response_body
        return repo_list