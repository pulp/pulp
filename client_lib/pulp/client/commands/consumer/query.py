from gettext import gettext as _

from pulp.client.commands.criteria import CriteriaCommand
from pulp.client.commands.options import OPTION_CONSUMER_ID
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliFlag, PulpCliOption
from pulp.client.parsers import parse_positive_int
from pulp.client.validators import iso8601_datetime_validator


class ConsumerListCommand(PulpCliCommand):
    """
    List the consumers that are currently registered with the Pulp server.
    """

    _ALL_FIELDS = ['id', 'display_name', 'description', 'bindings', 'notes']

    def __init__(self, context, name=None, description=None):
        name = name or 'list'
        description = description or _('lists a summary of consumers registered to the Pulp server')
        super(ConsumerListCommand, self).__init__(name, description, self.run)

        self.add_option(OPTION_FIELDS)

        self.add_flag(FLAG_BINDINGS)
        self.add_flag(FLAG_DETAILS)

        self.context = context
        self.api = context.server.consumer

    def run(self, **kwargs):
        details = kwargs.get(FLAG_DETAILS.keyword, False)

        consumer_list = self.get_consumer_list(kwargs)

        filters = order = self._ALL_FIELDS

        if details:
            order = self._ALL_FIELDS[:2]
            filters = None

        elif kwargs[OPTION_FIELDS.keyword]:
            filters = kwargs[OPTION_FIELDS.keyword].split(',')

            if 'bindings' not in filters:
                filters.append('bindings')
            if 'id' not in filters:
                filters.insert(0, 'id')

        self.context.prompt.render_title(self.get_title())

        for consumer in consumer_list:
            self.format_bindings(consumer)
            self.context.prompt.render_document(consumer, filters=filters, order=order)

    def get_consumer_list(self, kwargs):
        details = kwargs.get(FLAG_DETAILS.keyword, False)
        bindings = kwargs.get(FLAG_BINDINGS.keyword, False)

        response = self.api.consumers(details=details, bindings=bindings)
        return response.response_body

    def get_title(self):
        return _('Consumers')

    def format_bindings(self, consumer):
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


class ConsumerSearchCommand(CriteriaCommand):
    """
    Use search criteria to display consumers with specific traits.
    """

    def __init__(self, context, name=None, description=None):
        name = name or 'search'
        description = description or _('search consumers')
        super(ConsumerSearchCommand, self).__init__(self.run, name, description,
                                                    include_search=True)

        self.context = context
        self.api = context.server.consumer_search

    def run(self, **kwargs):
        consumer_list = self.get_consumer_list(kwargs)

        for consumer in consumer_list:
            self.context.prompt.render_document(consumer)

    def get_consumer_list(self, kwargs):
        consumer_list = self.api.search(**kwargs)
        return consumer_list


class ConsumerHistoryCommand(PulpCliCommand):
    """
    List the recorded events for a given consumer.
    """

    _ALL_FIELDS = ['consumer_id', 'type', 'details', 'originator', 'timestamp']

    def __init__(self, context, name=None, description=None):
        name = name or 'history'
        description = description or _('displays the history of operations on a consumer')
        super(ConsumerHistoryCommand, self).__init__(name, description, self.run)

        self.add_option(OPTION_CONSUMER_ID)
        self.add_option(OPTION_EVENT_TYPE)
        self.add_option(OPTION_LIMIT)
        self.add_option(OPTION_SORT)
        self.add_option(OPTION_START_DATE)
        self.add_option(OPTION_END_DATE)

        self.context = context
        self.api = context.server.consumer_history

    def run(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        event_type = kwargs[OPTION_EVENT_TYPE.keyword]
        limit = kwargs[OPTION_LIMIT.keyword]
        sort = kwargs[OPTION_SORT.keyword]
        start_date = kwargs[OPTION_START_DATE.keyword]
        end_date = kwargs[OPTION_END_DATE.keyword]

        self.context.prompt.render_title(_('Consumer History [ %(c)s ]') % {'c': consumer_id})

        response = self.api.history(consumer_id, event_type, limit, sort, start_date, end_date)
        event_list = response.response_body

        filters = order = self._ALL_FIELDS

        for event in event_list:
            self.context.prompt.render_document(event, filters=filters, order=order)

# options and flags ------------------------------------------------------------

OPTION_FIELDS = PulpCliOption('--fields',
                              _('comma-separated list of consumer fields; if specified only the'
                                ' given fields will be displayed'),
                              required=False)

OPTION_EVENT_TYPE = PulpCliOption('--event-type',
                                  _('limits displayed history entries to the given type; supported '
                                    'types: ("consumer_registered", "consumer_unregistered", '
                                    '"repo_bound", "repo_unbound", "content_unit_installed", '
                                    '"content_unit_uninstalled", "unit_profile_changed", '
                                    '"added_to_group", "removed_from_group")'),
                                  required=False)

OPTION_LIMIT = PulpCliOption('--limit',
                             _('limits displayed history entries to the given amount'
                               ' (must be greater than zero)'),
                             required=False,
                             parse_func=parse_positive_int)

OPTION_SORT = PulpCliOption('--sort',
                            _('indicates the sort direction ("ascending" or "descending") '
                              'based on the entry\'s timestamp'),
                            required=False)

OPTION_START_DATE = PulpCliOption('--start-date',
                                  _('only return entries that occur on or after the given date in'
                                    ' iso8601 format (yyyy-mm-ddThh:mm:ssZ)'),
                                  required=False,
                                  validate_func=iso8601_datetime_validator)

OPTION_END_DATE = PulpCliOption('--end-date',
                                _('only return entries that occur on or before the given date in '
                                  'iso8601 format (yyyy-mm-ddThh:mm:ssZ)'),
                                required=False,
                                validate_func=iso8601_datetime_validator)

FLAG_DETAILS = PulpCliFlag('--details',
                           _('if specified, all of the consumer information is displayed'))

FLAG_BINDINGS = PulpCliFlag('--bindings', _('if specified, the bindings information is displayed'))
