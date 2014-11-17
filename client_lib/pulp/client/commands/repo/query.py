from gettext import gettext as _

from pulp.client.commands.criteria import CriteriaCommand
from pulp.common import constants


DESC_SEARCH = _('searches for repositories on the server')


class RepoSearchCommand(CriteriaCommand):
    """
    Searches for repositories using the normal criteria search features
    """

    def __init__(self, context, repo_type, name=None):
        """
        :type context:      pulp.client.extensions.core.ClientContext
        :param repo_type:   value identifying the type of repository. Each set of
                            extensions is responsible for providing this value.
        :type  repo_type:   str
        """
        name = name or 'search'
        super(RepoSearchCommand, self).__init__(self.run, name=name,
                                                description=DESC_SEARCH,
                                                include_search=True)

        self.context = context
        self.prompt = context.prompt
        self.repo_type = repo_type

    def run(self, **kwargs):
        self.prompt.render_title(_('Repositories'))

        # Limit to only repositories of a specific type
        if kwargs.get('str-eq', None) is None:
            kwargs['str-eq'] = []
        kwargs['str-eq'].append(['notes.%s' % constants.REPO_NOTE_TYPE_KEY, self.repo_type])

        # Server call
        repo_list = self.context.server.repo_search.search(**kwargs)

        # Display the results
        order = ['id', 'display_name', 'description']
        self.prompt.render_document_list(repo_list, order=order)
