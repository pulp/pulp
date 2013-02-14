# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from gettext import gettext as _

from pulp.client.commands.criteria import CriteriaCommand
from pulp.client.commands.options import OPTION_CONSUMER_ID
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliFlag, PulpCliOption

# consumer query commands ------------------------------------------------------

class ConsumerListCommand(PulpCliCommand):
    """
    List the consumers that are currently registered with the Pulp server.
    """

    _all_fields = ['id', 'display_name', 'description', 'bindings', 'notes']

    def __init__(self, context, name=None, description=None):
        name = name or 'list'
        description = description or _('lists summary of consumers registered to the Pulp server')
        super(self.__class__, self).__init__(name, description, self.list)

        self.add_option(OPTION_FIELDS)

        self.add_flag(FLAG_BINDINGS)
        self.add_flag(FLAG_DETAILS)

        self.context = context
        self.api = context.server.consumer

    def list(self, **kwargs):
        details = kwargs.get(FLAG_DETAILS.keyword, False)
        bindings = kwargs.get(FLAG_BINDINGS.keyword, False)

        response = self.api.consumers(details=details, bindings=bindings)

        filters = order = self._all_fields

        if details:
            order = self._all_fields[:2]
            filters = None

        elif kwargs[OPTION_FIELDS.keyword]:
            filters = kwargs[OPTION_FIELDS.keyword].split(',')

            if 'bindings' not in filters:
                filters.append('bindings')
            if 'id' not in filters:
                filters.insert(0, 'id')

        self.context.prompt.render_title(_('Consumers'))

        for consumer in response.response_body:
            _format_bindings(consumer)
            self.context.prompt.render_document(consumer, filters=filters, order=order)


class ConsumerSearchCommand(CriteriaCommand):
    """
    Use search criteria to display consumers with specific traits.
    """

    def __init__(self, context, name=None, description=None):
        name = name or 'search'
        description = description or _('search consumers')
        super(self.__class__, self).__init__(self.search, name, description, include_search=True)

        self.context = context
        self.api = context.server.consumer_search

    def search(self, **kwargs):
        consumer_list = self.api.search(**kwargs)

        for consumer in consumer_list:
            self.context.prompt.render_document(consumer)


class ConsumerHistoryCommand(PulpCliCommand):
    """
    List the recorded events for a give consumer.
    """

    _all_fields = ['consumer_id', 'type', 'details', 'originator', 'timestamp']

    def __init__(self, context, name=None, description=None):
        name = name or 'history'
        description = description or _('displays the history of operations on a consumer')
        super(self.__class__, self).__init__(name, description, self.history)

        self.add_option(OPTION_CONSUMER_ID)
        self.add_option(OPTION_EVENT_TYPE)
        self.add_option(OPTION_LIMIT)
        self.add_option(OPTION_SORT)
        self.add_option(OPTION_START_DATE)
        self.add_option(OPTION_END_DATE)

        self.context = context
        self.api = context.server.consumer_history

    def history(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        event_type = kwargs[OPTION_EVENT_TYPE.keyword]
        limit = kwargs[OPTION_LIMIT.keyword]
        sort = kwargs[OPTION_SORT.keyword]
        start_date = kwargs[OPTION_START_DATE.keyword]
        end_date = kwargs[OPTION_END_DATE.keyword]

        self.context.prompt.render_title(_('Consumer History [ %(c)s ]') % {'c': consumer_id})

        response = self.api.history(consumer_id, event_type, limit, sort, start_date, end_date)
        event_list = response.response_body

        filters = order = self._all_fields

        for event in event_list:
            self.context.prompt.render_document(event, filters=filters, order=order)

# options and flags ------------------------------------------------------------

OPTION_FIELDS = PulpCliOption('--fields',
                              _('comma separated list of consumer fields; if specified only the given fields will be displayed'),
                              required=False)

OPTION_EVENT_TYPE = PulpCliOption('--event-type',
                                  _('limits displayed history entries to the given type; '
                                    'supported types: ("consumer_registered", "consumer_unregistered", "repo_bound", "repo_unbound",'
                                    '"content_unit_installed", "content_unit_uninstalled", "unit_profile_changed", "added_to_group",'
                                    '"removed_from_group")'),
                                  required=False)

OPTION_LIMIT = PulpCliOption('--limit',
                             _('limits displayed history entries to the given amount (must be greater than zero)'),
                             required=False)

OPTION_SORT = PulpCliOption('--sort',
                            _('indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp'),
                            required=False)

OPTION_START_DATE = PulpCliOption('--start-date',
                                  _('indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp'),
                                  required=False)

OPTION_END_DATE = PulpCliOption('--end-date',
                                _('indicates the sort direction ("ascending" or "descending") based on the entry\'s timestamp'),
                                required=False)

FLAG_DETAILS = PulpCliFlag('--details', _('if specified, all the consumer information is displayed'))

FLAG_BINDINGS = PulpCliFlag('--bindings', _('if specified, the bindings information is displayed'))


# utility functions ------------------------------------------------------------

def _format_bindings(consumer):
    bindings = consumer.get('bindings')

    if not bindings:
        return

    confirmed = []
    unconfirmed = []

    for binding in bindings:
        repo_id = binding['repo_id']

        if binding['deleted'] or len(binding['consumer_actions']):
            unconfirmed.append(repo_id)
        else:
            confirmed.append(repo_id)

    consumer['bindings'] = {'confirmed': confirmed, 'unconfirmed': unconfirmed}
