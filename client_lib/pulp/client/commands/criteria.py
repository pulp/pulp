from gettext import gettext as _

from okaara.cli import CommandUsage, OptionGroup

from pulp.client import parsers
from pulp.client import validators
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag
from pulp.common.compat import json


_LIMIT_DESCRIPTION = _('max number of items to return')
_SKIP_DESCRIPTION = _('number of items to skip')
_FILTERS_DESCRIPTION = _("""filters provided as JSON in Mongo syntax. This will
override any options specified from the 'Filters' section
below.""").replace('\n', ' ')
_FIELDS_DESCRIPTION = _("""comma-separated list of resource fields. Do not
include spaces. Default is all fields.""".replace('\n', ' '))
_SORT_DESCRIPTION = _("""field name, a comma, and either the word "ascending" or
"descending". The comma and direction are optional, and the direction
defaults to ascending. Do not put a space before or after the comma. For
multiple fields, use this option multiple times. Each one will be applied in
the order supplied.""".replace('\n', ' '))
_SEARCH_DESCRIPTION = _("""search items while optionally specifying sort, limit,
skip, and requested fields""".replace('\n', ' '))
_USAGE = _("""These are basic filtering options that will be AND'd together.
These will be ignored if --filters= is specified. Any option may be specified
multiple times. The value for each option should be a field name and value to
match against, specified as "name=value".
Example: $ pulp-admin <command> --str-eq="id=<repo_id>"
""").replace('\n', ' ')

ALL_CRITERIA_ARGS = ('filters', 'after', 'before', 'str-eq', 'int-eq', 'match',
                     'in', 'not', 'gt', 'gte', 'lt', 'lte')


class CriteriaCommand(PulpCliCommand):
    """
    Provides arguments for accepting a Pulp criteria. This can be used for both
    selective criteria and search criteria, the latter adding options for
    display arguments such as pagination and sorting.
    """

    def __init__(self, method, name=None, description=None, filtering=True,
                 include_search=True, *args, **kwargs):
        """
        :param name: name used to invoke the command
        :type  name: str
        :param description: user-readable text describing the command
        :type  description: str
        :param method:  A method to call when this command is executed. See
                        okaara docs for more info
        :type  method:  callable
        :param filtering:   if True, the command will add all filtering options
        :type  filtering:   bool
        :param include_search: if True, the command will add all non-filter
                               criteria options such as limit, seek, sort, etc.
        :type  include_search: bool
        """
        name = name or kwargs.pop('name', None) or 'search'
        description = description or kwargs.pop('description', None) or _SEARCH_DESCRIPTION

        PulpCliCommand.__init__(self, name, description, method, **kwargs)

        # Hang on to these so unit tests can verify the command is configuration
        self.filtering = filtering
        self.include_search = include_search

        if filtering:
            self.add_filtering()
        if include_search:
            self.add_display_criteria_options()

    def add_filtering(self):
        self.add_option(PulpCliOption('--filters', _FILTERS_DESCRIPTION,
                                      required=False, parse_func=json.loads))

        filter_group = OptionGroup('Filters', _(_USAGE))

        m = _('match where a named attribute equals a string value exactly.')
        filter_group.add_option(PulpCliOption(
            '--str-eq', m, required=False, allow_multiple=True, parse_func=self._parse_key_value
        ))

        m = _('match where a named attribute equals an int value exactly.')
        filter_group.add_option(PulpCliOption(
            '--int-eq', m, required=False, allow_multiple=True, parse_func=self._parse_key_value)
        )

        m = _('for a named attribute, match a regular expression using the mongo regex engine.')
        filter_group.add_option(PulpCliOption(
            '--match', m, required=False, allow_multiple=True, parse_func=self._parse_key_value
        ))

        m = _('for a named attribute, match where value is in the provided list of values, '
              'expressed as one row of CSV')
        filter_group.add_option(PulpCliOption(
            '--in', m, required=False, allow_multiple=True, parse_func=self._parse_key_value
        ))

        m = _('field and expression to omit when determining units for inclusion')
        filter_group.add_option(PulpCliOption(
            '--not', m, required=False, allow_multiple=True, parse_func=self._parse_key_value
        ))

        m = _('matches resources whose value for the specified field is greater than the'
              ' given value')
        filter_group.add_option(PulpCliOption(
            '--gt', m, required=False, allow_multiple=True, parse_func=self._parse_key_value
        ))

        m = _('matches resources whose value for the specified field is greater than or equal to '
              'the given value')
        filter_group.add_option(PulpCliOption(
            '--gte', m, required=False, allow_multiple=True, parse_func=self._parse_key_value
        ))

        m = _('matches resources whose value for the specified field is less than the given value')
        filter_group.add_option(PulpCliOption(
            '--lt', m, required=False, allow_multiple=True, parse_func=self._parse_key_value
        ))

        m = _('matches resources whose value for the specified field is less than or equal to the '
              'given value')
        filter_group.add_option(PulpCliOption(
            '--lte', m, required=False, allow_multiple=True, parse_func=self._parse_key_value
        ))

        self.add_option_group(filter_group)

    def add_display_criteria_options(self):
        """
        Add the full set of criteria-based search features to this command,
        including limit, skip, sort, and fields.
        """
        self.add_option(PulpCliOption('--limit', _LIMIT_DESCRIPTION,
                                      required=False, parse_func=int,
                                      validate_func=validators.positive_int_validator))
        self.add_option(PulpCliOption('--skip', _SKIP_DESCRIPTION,
                                      required=False, parse_func=int,
                                      validate_func=validators.non_negative_int_validator))
        self.add_option(PulpCliOption('--sort', _SORT_DESCRIPTION,
                                      required=False, allow_multiple=True,
                                      validate_func=self._validate_sort,
                                      parse_func=self._parse_sort))
        self.add_option(PulpCliOption('--fields', _FIELDS_DESCRIPTION,
                                      required=False, validate_func=str,
                                      parse_func=lambda x: x.split(',')))

    @staticmethod
    def ensure_criteria(kwargs):
        """
        Ensures at least one of the criteria options is specified in the
        given arguments. Other values may be specified in here and not
        affect the outcome.

        @param kwargs: keyword arguments parsed by the framework

        @raise CommandUsage: if there isn't at least one criteria argument
        """
        criteria_args = [k for k, v in kwargs.items() if k in ALL_CRITERIA_ARGS and v is not None]
        if len(criteria_args) == 0:
            raise CommandUsage()

    @staticmethod
    def _parse_key_value(args):
        """
        parses the raw user input, taken as a list of strings in the format
        'name=value', into a list of tuples in the format (name, value).

        :param args:    list of raw strings passed by the user on the command
                        line.
        :type  args:    list of basestrings

        :return:    new list of tuples in the format (name, value)
        """
        ret = []
        for arg in args:
            components = arg.split('=', 1)
            if len(components) != 2:
                raise ValueError('key and value must be separated by "="')
            ret.append(components)
        return ret

    @classmethod
    def _validate_sort(cls, sort_args):
        """
        validates that each individual sort arg starts with a field name, and
        if a direction is included, that it is either 'ascending' or
        'descending'.

        @param sort_args:   list of search arguments. Each is in the format
                            'field_name,direction' where direction is
                            'ascending' or 'descending'.
        @type  sort_args:   list
        """
        for arg in sort_args:
            field_name, direction = cls._explode_sort_arg_pieces(str(arg))
            if len(field_name) == 0:
                raise ValueError(_('field name must be specified'))
            if direction not in ('ascending', 'descending'):
                raise ValueError(_('direction must be "ascending" or "descending"'))

    @classmethod
    def _parse_sort(cls, sort_args):
        """
        Parse the sort argument to a search command

        @param sort_args:   list of search arguments. Each is in the format
                            'field_name,direction' where direction is
                            'ascending' or 'descending'.
        @type  sort_args:   list

        @return:    list of sort arguments in the format expected by Criteria
        @rtype:     list
        """
        ret = []
        for value in sort_args:
            field_name, direction = cls._explode_sort_arg_pieces(value)
            if direction not in ('ascending', 'descending'):
                # validation should have caught this
                raise CommandUsage()
            ret.append((field_name, direction))

        return ret

    @staticmethod
    def _explode_sort_arg_pieces(sort_arg):
        """
        Takes an individual sort argument and returns the two components:
        field_name, and direction. If direction is not supplied, it defaults
        to 'ascending'.

        @param sort_arg:    argument passed from user as --sort=
        @type  sort_arg:    str

        @return:    tuple of field name and direction
        @rtype:     tuple of 2 basestrings
        """
        pieces = sort_arg.lower().split(',')
        field_name = pieces[0]
        # the join just helps us create a string from an array with
        # one or zero members.
        direction = ''.join(pieces[1:2]) or 'ascending'
        return field_name, direction


class UnitAssociationCriteriaCommand(CriteriaCommand):
    """
    Provides the full suite of criteria flags plus those relevant only when
    specifying unit associations. This command should be used in cases where
    the command is trying to capture a set of unit associations to act on.
    By comparison, if the command is looking to display unit associations to
    the user, the DisplayUnitAssociationsCommand is preferred as it adds
    display-specific flags to these.
    """

    def __init__(self, method, *args, **kwargs):
        """
        @param method: method that should be invoked when the command is executed
        @type  method: callable
        """
        CriteriaCommand.__init__(self, method, *args, **kwargs)

        self.add_repo_id_option()

        m = _('matches units added to the source repository on or after the given time; '
              'specified as a timestamp in iso8601 format')
        self.create_option('--after', m, ['-a'], required=False,
                           allow_multiple=False, parse_func=parsers.iso8601)

        m = _('matches units added to the source repository on or before the given time; '
              'specified as a timestamp in iso8601 format')
        self.create_option('--before', m, ['-b'], required=False,
                           allow_multiple=False, parse_func=parsers.iso8601)

    def add_repo_id_option(self):
        """
        Override this method to a no-op to skip adding the repo id option.
        """
        self.add_option(PulpCliOption('--repo-id',
                                      _('identifies the repository to search within'),
                                      required=True))


class DisplayUnitAssociationsCommand(UnitAssociationCriteriaCommand):
    """
    Provides the full suite of unit association criteria flags along with
    extra flags to control the output of what will be displayed about the
    associations. The typical usage of this command is when searching or
    displaying unit associations to the user.
    """

    ASSOCIATION_FLAG = PulpCliFlag(
        '--details', _('show association details'), aliases=['-d'])

    def __init__(self, method, *args, **kwargs):
        super(DisplayUnitAssociationsCommand, self).__init__(
            method, *args, **kwargs
        )

        # If we support more than just the details flag in the future, those
        # options will be added here

        self.add_flag(self.ASSOCIATION_FLAG)
