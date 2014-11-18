"""
Commands for showing a repository's sync and publish history
"""

from gettext import gettext as _

from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.extensions.extensions import PulpCliOption, PulpCliFlag, PulpCliCommand
from pulp.client import validators


# The default limit on the number of history entries to display
REPO_HISTORY_LIMIT = 5

# Descriptions
DESC_DETAILS = _('if specified, all history information is displayed')
DESC_DISTRIBUTOR_ID = _('the distributor id to display history entries for')
DESC_END_DATE = _('only return entries that occur on or before the given date in iso8601 format'
                  ' (yyyy-mm-ddThh:mm:ssZ)')
DESC_LIMIT = _(
    'limits displayed history entries to the given amount (must be greater than zero); the default'
    ' is %(limit)s' % {'limit': REPO_HISTORY_LIMIT})
DESC_PUBLISH_HISTORY = _('displays the history of publish operations on a repository')
DESC_SORT = _('indicates the sort direction ("ascending" or "descending") based on the timestamp')
DESC_SYNC_HISTORY = _('displays the history of sync operations on a repository')
DESC_START_DATE = _('only return entries that occur on or after the given date in iso8601 format'
                    ' (yyyy-mm-ddThh:mm:ssZ)')

# Options
OPTION_END_DATE = PulpCliOption('--end-date', DESC_END_DATE, required=False,
                                validate_func=validators.iso8601_datetime_validator)
OPTION_LIMIT = PulpCliOption('--limit', DESC_LIMIT, required=False,
                             validate_func=validators.positive_int_validator)
OPTION_SORT = PulpCliOption('--sort', DESC_SORT, required=False)
OPTION_DISTRIBUTOR_ID = PulpCliOption('--distributor-id', DESC_DISTRIBUTOR_ID, required=True,
                                      validate_func=validators.id_validator)
OPTION_START_DATE = PulpCliOption('--start-date', DESC_START_DATE, required=False,
                                  validate_func=validators.iso8601_datetime_validator)

# Flags
FLAG_DETAILS = PulpCliFlag('--details', DESC_DETAILS, aliases='-d')


class SyncHistoryCommand(PulpCliCommand):
    """
    Displays the sync history of a given repository
    """

    def __init__(self, context, name='sync', description=DESC_SYNC_HISTORY):
        """
        :param context: The client context used to interact with the client framework and server
        :type context: pulp.client.extensions.core.ClientContext

        :param name: The name of the command in the history section
        :type name: str

        :param description: The description to use in the cli
        :type description: str
        """

        # The context is used to access the server and prompt.
        self.context = context

        super(SyncHistoryCommand, self).__init__(name, description, self.run)

        self.add_option(OPTION_REPO_ID)
        self.add_option(OPTION_LIMIT)
        self.add_option(OPTION_SORT)
        self.add_option(OPTION_START_DATE)
        self.add_option(OPTION_END_DATE)
        self.add_flag(FLAG_DETAILS)
        self.fields_to_display = ['repo_id', 'result', 'started', 'completed', 'added_count',
                                  'removed_count', 'updated_count']

    def run(self, **user_input):
        """
        The action to take when the sync history command is executed

        :param user_input: the options and flags provided by the user
        :type user_input: dict
        """

        # Collect input
        repo_id = user_input[OPTION_REPO_ID.keyword]
        if user_input[OPTION_LIMIT.keyword] is not None:
            limit = int(user_input[OPTION_LIMIT.keyword])
        else:
            limit = REPO_HISTORY_LIMIT
        start_date = user_input[OPTION_START_DATE.keyword]
        end_date = user_input[OPTION_END_DATE.keyword]
        sort = user_input[OPTION_SORT.keyword]
        details = user_input[FLAG_DETAILS.keyword]

        # Request the sync history from the server
        sync_list = self.context.server.repo_history.sync_history(repo_id, limit, sort, start_date,
                                                                  end_date).response_body

        # Filter the fields to show and define the order in which they are displayed
        if details is True:
            self.fields_to_display.append('summary')
            self.fields_to_display.append('details')
        filters = order = self.fields_to_display

        # Render results
        title = _('Sync History [ %(repo)s ]') % {'repo': repo_id}
        self.context.prompt.render_title(title)
        self.context.prompt.render_document_list(sync_list, filters=filters, order=order)


class PublishHistoryCommand(PulpCliCommand):
    """
    Displays the publish history of a given repository and publisher
    """

    def __init__(self, context, name='publish', description=DESC_PUBLISH_HISTORY):
        """
        :param context: The client context used to interact with the client framework and server
        :type context: pulp.client.extensions.core.ClientContext

        :param name: The name of the command in the history section
        :type name: str

        :param description: The description to use in the cli
        :type description: str
        """

        # The context is used to access the server and prompt.
        self.context = context

        super(PublishHistoryCommand, self).__init__(name, description, self.run)

        # History is given for a repo id and distributor id pair, so these are mandatory
        self.add_option(OPTION_REPO_ID)
        self.add_option(OPTION_DISTRIBUTOR_ID)
        self.add_option(OPTION_LIMIT)
        self.add_option(OPTION_SORT)
        self.add_option(OPTION_START_DATE)
        self.add_option(OPTION_END_DATE)
        self.add_flag(FLAG_DETAILS)
        # Set the default fields to display
        self.fields_to_display = ['repo_id', 'distributor_id', 'result', 'started', 'completed']

    def run(self, **user_input):
        """
        The action to take when the sync history command is executed

        :param user_input: the options and flags provided by the user
        :type user_input: dict
        """

        # Collect input
        repo_id = user_input[OPTION_REPO_ID.keyword]
        distributor_id = user_input[OPTION_DISTRIBUTOR_ID.keyword]
        if user_input[OPTION_LIMIT.keyword] is not None:
            limit = int(user_input[OPTION_LIMIT.keyword])
        else:
            limit = REPO_HISTORY_LIMIT
        start_date = user_input[OPTION_START_DATE.keyword]
        end_date = user_input[OPTION_END_DATE.keyword]
        sort = user_input[OPTION_SORT.keyword]
        details = user_input[FLAG_DETAILS.keyword]

        # Request the publish history from the server
        publish_list = self.context.server.repo_history.publish_history(repo_id, distributor_id,
                                                                        limit, sort, start_date,
                                                                        end_date)
        publish_list = publish_list.response_body

        # Filter the fields to show and define the order in which they are displayed
        if details is True:
            self.fields_to_display.append('summary')
            self.fields_to_display.append('details')
        filters = order = self.fields_to_display

        # Render results
        title = _('Publish History [ %(repo)s ]') % {'repo': repo_id}
        self.context.prompt.render_title(title)
        self.context.prompt.render_document_list(publish_list, filters=filters, order=order)
