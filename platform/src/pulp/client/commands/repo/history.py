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

from gettext import gettext as _

from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption
from pulp.client import validators
from pulp.bindings.repository import RepositoryHistoryAPI
from pulp.client.extensions.core import PulpPrompt

# -- constants ----------------------------------------------------------------

# Command descriptions
DESC_SYNC_HISTORY = _('shows sync history')
DESC_PUBLISH_HISTORY = _('shows publish history')

# Limit is used to limit the number of history events shown
DESC_LIMIT = _('specify how many events to display')
OPTION_LIMIT = PulpCliOption('--limit', DESC_LIMIT, required=False,
                             validate_func=validators.positive_int_validator)
DEFAULT_LIMIT = 5

# -- commands -----------------------------------------------------------------


class SyncHistoryCommand(PulpCliCommand):
    """
    Displays the sync history of a given repository
    """

    def __init__(self, context, name='sync_history', description=DESC_SYNC_HISTORY, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(SyncHistoryCommand, self).__init__(name, description, method)

        self.add_option(OPTION_REPO_ID)
        self.add_option(OPTION_LIMIT)

    # TODO: Figure out where to apply the limit
    def run(self, **kwargs):
        # Collect input
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        limit = DEFAULT_LIMIT
        if kwargs[OPTION_LIMIT.keyword] is not None:
            limit = kwargs[OPTION_LIMIT.keyword]

        result = self.context.server.repo_history.sync_history(repo_id)

        # TODO: render the theoretical results in a pretty way


class PublishHistoryCommand(PulpCliCommand):
    """

    """

    def __init__(self, context, name='publish_history', description=DESC_PUBLISH_HISTORY, method=None):
        self.context = context
        self.prompt = context.prompt

        if method is None:
            method = self.run

        super(PublishHistoryCommand, self).__init__(name, description, method)

        self.add_option(OPTION_REPO_ID)
        self.add_option(OPTION_LIMIT)

    # TODO: Is a second required arg necessary?
    def run(self, **kwargs):
        # Collect input
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        limit = DEFAULT_LIMIT
        if kwargs[OPTION_LIMIT.keyword] is not None:
            limit = kwargs[OPTION_LIMIT.keyword]