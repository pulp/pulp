"""
Contains reusable, expandable commands for the lifecycle and listing of
repository groups, including manipulation of their membership.

Customization of the commands in this module can be done either by specifying
a method to the command's constructor or by subclassing and overriding the
``run(self, **kwargs)`` method.

Subclasses should be sure to call the super class constructor to ensure the
default options to the command are added. The subclass can then add any
additional options as necessary for its custom behavior.
"""

import copy
from gettext import gettext as _

from pulp.bindings.exceptions import NotFoundException
from pulp.client.commands.criteria import CriteriaCommand
from pulp.client.commands.options import (OPTION_REPO_ID, OPTION_DESCRIPTION,
                                          OPTION_NAME, OPTION_NOTES, OPTION_GROUP_ID, FLAG_ALL)
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliFlag, PulpCliOption
from pulp.common import compat


# Group CUDL Command Descriptions
DESC_CREATE = _('creates a new repository group')
DESC_UPDATE = _('updates the metadata about the group itself (not its members)')
DESC_DELETE = _('deletes a repository group')
DESC_LIST = _('lists repository groups on the Pulp server')
DESC_SEARCH = _('searches for repository groups on the Pulp server')

# Member Command Descriptions
DESC_MEMBER_LIST = _('lists repositories in a repository group')
DESC_MEMBER_ADD = _('adds repositories to an existing repository group')
DESC_MEMBER_REMOVE = _('removes repositories from a repository group')

# Defaults to pass to render_document_list when displaying groups
DEFAULT_FILTERS = ['id', 'display_name', 'description', 'repo_ids', 'notes']
DEFAULT_ORDER = DEFAULT_FILTERS


class CreateRepositoryGroupCommand(PulpCliCommand):
    """
    Creates a new repository group in Pulp. One or more repositories can be
    added at creation time through this command.
    """

    def __init__(self, context, name='create', description=DESC_CREATE, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(CreateRepositoryGroupCommand, self).__init__(name, description, method)

        self.add_option(OPTION_GROUP_ID)
        self.add_option(OPTION_NAME)
        self.add_option(OPTION_DESCRIPTION)
        self.add_option(OPTION_NOTES)

    def run(self, **kwargs):
        # Collect input
        id = kwargs[OPTION_GROUP_ID.keyword]
        name = id
        if OPTION_NAME.keyword in kwargs:
            name = kwargs[OPTION_NAME.keyword]
        description = kwargs[OPTION_DESCRIPTION.keyword]

        notes = kwargs.get(OPTION_NOTES.keyword, None)

        # Call the server
        self.context.server.repo_group.create(id, name, description, notes)
        msg = _('Repository Group [%(g)s] successfully created')
        self.prompt.render_success_message(msg % {'g': id})


class DeleteRepositoryGroupCommand(PulpCliCommand):
    """
    Deletes a repository group from the Pulp server.
    """

    def __init__(self, context, name='delete', description=DESC_DELETE, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(DeleteRepositoryGroupCommand, self).__init__(name, description, method)

        self.add_option(OPTION_GROUP_ID)

    def run(self, **kwargs):
        id = kwargs[OPTION_GROUP_ID.keyword]

        try:
            self.context.server.repo_group.delete(id)
            msg = _('Repository group [%(g)s] successfully deleted')
            self.prompt.render_success_message(msg % {'g': id})
        except NotFoundException:
            msg = _('Repository group [%(g)s] does not exist on the server')
            self.prompt.write(msg % {'g': id}, tag='not-found')


class UpdateRepositoryGroupCommand(PulpCliCommand):
    """
    Updates the metadata about a repository group (but not its members).
    """

    def __init__(self, context, name='update', description=DESC_UPDATE, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(UpdateRepositoryGroupCommand, self).__init__(name, description, method)

        self.add_option(OPTION_GROUP_ID)
        self.add_option(OPTION_NAME)
        self.add_option(OPTION_DESCRIPTION)
        self.add_option(OPTION_NOTES)

    def run(self, **kwargs):
        # Assemble the delta for all options that were passed in
        delta = dict([(k, v) for k, v in kwargs.items() if v is not None])
        delta.pop(OPTION_GROUP_ID.keyword)  # not needed in the delta

        # Conversion between arg hyphens and server-side underscores
        if delta.get(OPTION_NAME.keyword, None) is not None:
            delta['display_name'] = delta.pop(OPTION_NAME.keyword)

        if delta.pop(OPTION_NOTES.keyword, None) is not None:
            delta['notes'] = kwargs[OPTION_NOTES.keyword]

        try:
            self.context.server.repo_group.update(kwargs[OPTION_GROUP_ID.keyword], delta)
            msg = 'Repo group [%(g)s] successfully updated'
            self.prompt.render_success_message(msg % {'g': kwargs['group-id']})
        except NotFoundException:
            msg = 'Repo group [%(g)s] does not exist on the server'
            self.prompt.write(msg % {'g': kwargs['group-id']}, tag='not-found')


class ListRepositoryGroupsCommand(PulpCliCommand):
    """
    Lists repository groups in the Pulp server.
    """

    def __init__(self, context, name='list', description=DESC_LIST, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(ListRepositoryGroupsCommand, self).__init__(name, description, method)

        self.add_option(PulpCliFlag('--details', _('if specified, all the repo group information '
                                                   'is displayed')))
        self.add_option(PulpCliOption('--fields', _('comma-separated list of repo group fields; if '
                                                    'specified, only the given fields will '
                                                    'displayed'),
                                      required=False))

    def run(self, **kwargs):
        self.prompt.render_title(_('Repository Groups'))

        repo_group_list = self.context.server.repo_group.repo_groups().response_body

        filters = DEFAULT_FILTERS
        order = DEFAULT_ORDER

        if kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'id' not in filters:
                filters.append('id')
            order = ['id']

        if len(repo_group_list) > 0:
            self.prompt.render_document_list(repo_group_list,
                                             filters=filters,
                                             order=order)
        else:
            self.prompt.render_paragraph(_('No repository groups found'), tag='not-found')


class SearchRepositoryGroupsCommand(CriteriaCommand):
    """
    Uses criteria to search for repository groups.
    """

    def __init__(self, context, name='search', description=DESC_SEARCH, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(SearchRepositoryGroupsCommand, self).__init__(method, name=name,
                                                            description=description,
                                                            include_search=True)

    def run(self, **kwargs):
        self.prompt.render_title(_('Repository Groups'))

        repo_group_list = self.context.server.repo_group_search.search(**kwargs)
        self.prompt.render_document_list(repo_group_list,
                                         order=DEFAULT_ORDER)


class ListRepositoryGroupMembersCommand(PulpCliCommand):
    """
    Lists repositories in a single repository group.
    """

    def __init__(self, context, name='list', description=DESC_MEMBER_LIST, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(ListRepositoryGroupMembersCommand, self).__init__(name, description, method)

        self.add_option(OPTION_GROUP_ID)

    def run(self, **kwargs):
        self.prompt.render_title(_('Repository Group Members'))

        group_id = kwargs[OPTION_GROUP_ID.keyword]
        criteria = {'fields': ('repo_ids',), 'filters': {'id': group_id}}
        repo_group_list = self.context.server.repo_group_search.search(**criteria)

        filters = ['id', 'display_name', 'description', 'content_unit_counts', 'notes']
        order = filters

        if len(repo_group_list) != 1:
            self.prompt.write('Repo group [%s] does not exist on the server' % group_id,
                              tag='not-found')
        else:
            repo_ids = repo_group_list[0].get('repo_ids')
            if repo_ids and len(repo_ids) > 0:
                criteria = {'filters': {'id': {'$in': repo_ids}}}
                repo_list = self.context.server.repo_search.search(**criteria)
                self.prompt.render_document_list(repo_list, filters=filters, order=order)
            else:
                msg = _('No matching repositories found')
                self.prompt.render_paragraph(msg, tag='no-members')


class RepositoryGroupMembersCommand(CriteriaCommand):
    """
    Base class that adds options, enforces behavior with respect to the --all
    flag, and adds an optional list of repo IDs to the criteria.
    """

    def __init__(self, context, name, description, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(RepositoryGroupMembersCommand, self).__init__(
            method, name=name, description=description, include_search=False
        )

        self.add_option(OPTION_GROUP_ID)
        self.add_flag(FLAG_ALL)

        # Copy the repo ID option so we can dork with it
        repo_id_option = copy.copy(OPTION_REPO_ID)
        repo_id_option.required = False
        repo_id_option.allow_multiple = True
        self.add_option(repo_id_option)

    def run(self, **kwargs):
        group_id = kwargs.pop(OPTION_GROUP_ID.keyword)
        if not compat.any(kwargs.values()):
            self.prompt.render_failure_message(
                _('At least one matching option must be provided.'))
            return
        del kwargs[FLAG_ALL.keyword]
        repo_ids = kwargs.pop(OPTION_REPO_ID.keyword)
        if repo_ids:
            # automatically add the supplied repo IDs to the search
            in_arg = kwargs.get('in') or []
            in_arg.append(('id', ','.join(repo_ids)))
            kwargs['in'] = in_arg

        self._action(group_id, **kwargs)

    def _action(self, group_id, **kwargs):
        """
        override this in base classes. It should call an appropriate remote
        method to execute an action.

        :param group_id:    primary key for a repo group
        :type  group_id:    str
        """
        raise NotImplementedError


class AddRepositoryGroupMembersCommand(RepositoryGroupMembersCommand):
    """
    Allows the user to specify Pulp criteria to select repositories to add
    to an existing group.
    """

    def __init__(self, context, name='add', description=DESC_MEMBER_ADD, method=None):
        super(AddRepositoryGroupMembersCommand, self).__init__(
            context, name, description, method)

    def _action(self, group_id, **kwargs):
        self.context.server.repo_group_actions.associate(group_id, **kwargs)

        msg = _('Successfully added members to repository group [%(g)s]')
        self.prompt.render_success_message(msg % {'g': group_id})


class RemoveRepositoryGroupMembersCommand(RepositoryGroupMembersCommand):
    """
    Allows the user to specify Pulp criteria to indicate repositories to remove
    from a group.
    """

    def __init__(self, context, name='remove', description=DESC_MEMBER_REMOVE, method=None):
        super(RemoveRepositoryGroupMembersCommand, self).__init__(
            context, name, description, method)

    def _action(self, group_id, **kwargs):
        self.context.server.repo_group_actions.unassociate(group_id, **kwargs)

        msg = _('Successfully removed members from repository group [%(g)s]')
        self.prompt.render_success_message(msg % {'g': group_id})
