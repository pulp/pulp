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
            delta['notes'] = kwargs[OPTION_NOTES.keyword]

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

    This command is set up to make a distinction between different "types" of
    repositories. The intention is to display details on repositories related
    to a particular support bundle, but also a brief indicator to the fact that
    other repositories exist in Pulp that are not related to the bundle. This
    second batch of repositories is referred to as, for lack of a better term,
    "other repositories".

    With this distinction, there are two methods to override that will return
    the two lists of repositories. If there is no desire to support the
    other repositories, the get_other_repositories method need not be overridden.
    That call will only be made if the --all flag is specified.

    Since the term "other repositories" is wonky, the header title for both
    the matching repositories and other repositories can be customized at
    instantiation time. For instance, the puppet support bundle may elect to
    set the title to "Puppet Repositories".

    :ivar repos_title: header to use when displaying the details of the first
          class repositories (returned from get_repositories)
    :type repos_title: str

    :ivar other_repos_title: header to use when displaying the list of other
          repositories
    :type other_repos_title: str

    :ivar include_all_flag: if true, the --all flag will be included to support
          displaying other repositories
    :type include_all_flag: bool
    """

    def __init__(self, context, name='list', description=DESC_LIST, method=None,
                 repos_title=None, other_repos_title=None, include_all_flag=True):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        self.repos_title = repos_title
        if self.repos_title is None:
            self.repos_title = _('Repositories')

        self.other_repos_title = other_repos_title
        if self.other_repos_title is None:
            self.other_repos_title = _('Other Pulp Repositories')

        super(ListRepositoriesCommand, self).__init__(name, description, method)

        d = _('if specified, detailed configuration information is displayed for each repository')
        self.add_option(PulpCliFlag('--details', d))

        d = _('comma-separated list of repository fields; if specified, only the given fields will displayed')
        self.add_option(PulpCliOption('--fields', d, required=False))

        self.supports_all = include_all_flag
        if self.supports_all:
            d = _('if specified, information on all Pulp repositories, regardless of type, will be displayed')
            self.add_option(PulpCliFlag('--all', d, aliases=['-a']))

    def run(self, **kwargs):
        self.display_repositories(**kwargs)

        if kwargs.get('all', False):
            self.display_other_repositories(**kwargs)

    def display_repositories(self, **kwargs):
        """
        Default formatting for displaying the repositories returned from the
        get_repositories method. This call may be overridden to customize
        the repository list appearance.
        """
        self.prompt.render_title(self.repos_title)

        # Default flags to render_document_list
        filters = ['id', 'display_name', 'description', 'content_unit_count']
        order = filters

        query_params = {}
        if kwargs['details']:
            filters.append('notes')
            for p in ('importers', 'distributors'):
                query_params[p] = True
                filters.append(p)
        elif kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'id' not in filters:
                filters.append('id')
            order = ['id']

        repo_list = self.get_repositories(query_params, **kwargs)
        self.prompt.render_document_list(repo_list, filters=filters, order=order)

    def display_other_repositories(self, **kwargs):
        """
        Default formatting for displaying the repositories returned from the
        get_other_repositories method. This call may be overridden to customize
        the repository list appearance.
        """
        self.prompt.render_title(self.other_repos_title)

        repo_list = self.get_other_repositories(None, **kwargs)

        filters = ['id', 'display_name']
        order = filters
        self.prompt.render_document_list(repo_list, filters=filters, order=order)

    def get_repositories(self, query_params, **kwargs):
        """
        Subclasses will want to override this to return a subset of repositories
        based on the goals of the subclass. For instance, a subclass whose
        responsibility is to display puppet repositories will only return
        the list of puppet repositories from this call.

        If not overridden, all repositories will be returned by default.

        The query_params parameter is a dictionary of tweaks to what data should
        be included for each repository. For example, this will contain the
        flags necessary to control whether or not to include importer and
        distributor information. In most cases, the overridden method will
        want to pass these directly to the bindings which will format them
        appropriately for the server-side call to apply them.

        @param query_params: see above
        @type  query_params: dict
        @param kwargs: all keyword args passed from the CLI framework into this
               command, including any that were added by a subclass
        @type  kwargs: dict

        @return: list of repositories to display as the first-class repositories
                 in this list command; the format should be the same as what is
                 returned from the server
        @rtype: list
        """
        repo_list = self.context.server.repo.repositories(query_params).response_body
        return repo_list

    def get_other_repositories(self, query_params, **kwargs):
        """
        Subclasses may want to override this to display all other repositories
        that do not match what the subclass goals are. For example, a subclass
        of this command that wants to display puppet repositories will return
        all non-puppet repositories from this call. These repositories will
        be displayed separately for the user so the user has the ability to see
        the full repository list from this command if so desired.

        While not strongly required, the expectation is that this call will be
        the inverse of what is returned from get_repositories. Put another way,
        the union of these results and get_repositories should be the full list
        of repositories in the Pulp server, while their intersection should be
        empty.

        This call will only be made if the user requests all repositories. If
        that flag is not specified, this call is skipped entirely.

        If not overridden, an empty list will be returned to indicate there
        were no extra repositories.

        The query_params parameter is a dictionary of tweaks to what data should
        be included for each repository. For example, this will contain the
        flags necessary to control whether or not to include importer and
        distributor information. In most cases, the overridden method will
        want to pass these directly to the bindings which will format them
        appropriately for the server-side call to apply them.

        @param query_params: see above
        @type  query_params: dict
        @param kwargs: all keyword args passed from the CLI framework into this
               command, including any that were added by a subclass
        @type  kwargs: dict

        @return: list of repositories to display as non-matching repositories
                 in this list command; the format should be the same as what is
                 returned from the server, the display method will take care
                 of choosing which data to display to the user.
        @rtype: list
        """
        return []
