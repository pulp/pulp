# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
Commands for showing a repository's sync and publish history
"""

from gettext import gettext as _

from okaara import parsers

from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.extensions.extensions import PulpCliOption, PulpCliFlag, PulpCliCommand
from pulp.client import validators

# -- constants ----------------------------------------------------------------

DEFAULT_LIMIT = 5

# Descriptions
DESC_DETAILS = _('if specified, all history information is displayed')
DESC_DISTRIBUTOR_ID = _('the distributor id')
DESC_END_DATE = _('only return entries that occur on or before the given date in iso8601 format'
                  ' (yyyy-mm-ddThh:mm:ssZ)')
DESC_LIMIT = _('limits displayed history entries to the given amount (must be greater than zero)')
DESC_PUBLISH_HISTORY = _('displays the history of publish operations on a repository')
DESC_SORT = _('indicates the sort direction ("ascending" or "descending") based on the timestamp')
DESC_SYNC_HISTORY = _('displays the history of sync operations on a repository')
DESC_START_DATE = _('only return entries that occur on or after the given date in iso8601 format'
                    ' (yyyy-mm-ddThh:mm:ssZ)')

# Options
OPTION_END_DATE = PulpCliOption('--end-date', DESC_END_DATE, required=False,
                                validate_func=validators.iso8601_datetime_validator)
OPTION_LIMIT = PulpCliOption('--limit', DESC_LIMIT, required=False,
                             parse_func=parsers.parse_positive_int)
OPTION_SORT = PulpCliOption('--sort', DESC_SORT, required=False)
OPTION_DISTRIBUTOR_ID = PulpCliOption('--distributor-id', DESC_DISTRIBUTOR_ID, required=True,
                                      validate_func=validators.id_validator)
OPTION_START_DATE = PulpCliOption('--start-date', DESC_START_DATE, required=False,
                                  validate_func=validators.iso8601_datetime_validator)

# Flags
FLAG_DETAILS = PulpCliFlag('--details', DESC_DETAILS, aliases='-d')

# -- commands -----------------------------------------------------------------


class SyncHistoryCommand(PulpCliCommand):
    """
    Displays the sync history of a given repository
    """

    def __init__(self, context, name='sync', description=DESC_SYNC_HISTORY):
        # The context is used to access the server and prompt.
        self.context = context

        super(SyncHistoryCommand, self).__init__(name, description, self.run)

        self.add_option(OPTION_REPO_ID)
        self.add_option(OPTION_LIMIT)
        self.add_option(OPTION_SORT)
        self.add_option(OPTION_START_DATE)
        self.add_option(OPTION_END_DATE)
        self.add_flag(FLAG_DETAILS)
        self.default_fields = ['repo_id', 'result', 'started', 'completed', 'added_count',
                               'removed_count', 'updated_count']

    def run(self, **kwargs):
        # Collect input
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        if kwargs[OPTION_LIMIT.keyword] is not None:
            limit = kwargs[OPTION_LIMIT.keyword]
        else:
            limit = DEFAULT_LIMIT
        start_date = kwargs[OPTION_START_DATE.keyword]
        end_date = kwargs[OPTION_END_DATE.keyword]
        sort = kwargs[OPTION_SORT.keyword]
        details = kwargs[FLAG_DETAILS.keyword]

        # Request the sync history from the server
        sync_list = self.context.server.repo_history.sync_history(repo_id, limit, sort, start_date,
                                                                  end_date).response_body

        # Filter the fields to show and define the order in which they are displayed
        if details is True:
            self.default_fields.append('summary')
            self.default_fields.append('details')
        filters = order = self.default_fields

        # Render results
        title = _('Sync History [ %(repo)s ]') % {'repo': repo_id}
        self.context.prompt.render_title(title)
        self.context.prompt.render_document_list(sync_list, filters=filters, order=order)


class PublishHistoryCommand(PulpCliCommand):
    """
    Displays the publish history of a given repository and publisher
    """

    def __init__(self, context, name='publish', description=DESC_PUBLISH_HISTORY):
        # The context is used to access the server and prompt.
        self.context = context

        super(PublishHistoryCommand, self).__init__(name, description, self.run)

        # History is given for a repo id and distributor id pair
        self.add_option(OPTION_REPO_ID)
        self.add_option(OPTION_DISTRIBUTOR_ID)
        # Optional limit on the number of history items to show
        self.add_option(OPTION_LIMIT)
        # Option flag to show more details for each history item
        self.add_flag(FLAG_DETAILS)
        # Set the default fields to display
        self.default_fields = ['repo_id', 'distributor_id', 'result', 'started', 'completed']

    def run(self, **kwargs):
        # Collect input
        details = kwargs[FLAG_DETAILS.keyword]
        distributor_id = kwargs[OPTION_DISTRIBUTOR_ID.keyword]
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        if kwargs[OPTION_LIMIT.keyword] is not None:
            limit = kwargs[OPTION_LIMIT.keyword]
        else:
            limit = DEFAULT_LIMIT

        # Request the publish history from the server
        publish_list = self.context.server.repo_history.publish_history(repo_id, distributor_id, limit)
        publish_list = publish_list.response_body

        # Filter the fields to show and define the order in which they are displayed
        if details is True:
            self.default_fields.append('summary')
            self.default_fields.append('details')
        filters = order = self.default_fields

        # Render results
        title = _('Publish History [ %(repo)s ]') % {'repo': repo_id}
        self.context.prompt.render_title(title)
        self.context.prompt.render_document_list(publish_list, filters=filters, order=order)