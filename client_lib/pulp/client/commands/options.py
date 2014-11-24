"""
Contains CLI framework option and flag instances for options that are used
across multiple command areas. Examples include specifying a repository ID or
specifying notes on a resource.

The option instances in this module should **NEVER** be modified; changes will
be reflected across the CLI. If changes need to be made, for instance changing
the required flag, a copy of the option should be created and the copy
manipulated with the desired changes.
"""

from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliOption, PulpCliFlag
from pulp.client import parsers, validators


# General Resource
DESC_ID = _('unique identifier; only alphanumeric, -, and _ allowed')
DESC_ID_ALLOWING_DOTS = _('unique identifier; only alphanumeric, ., -, and _ allowed')
DESC_NAME = _('user-readable display name (may contain i18n characters)')
DESC_DESCRIPTION = _('user-readable description (may contain i18n characters)')
DESC_NOTE = _(
    'adds/updates/deletes notes to programmatically identify the resource; '
    'key-value pairs must be separated by an equal sign (e.g. key=value); multiple notes can '
    'be changed by specifying this option multiple times; notes are deleted by '
    'specifying "" as the value')
DESC_ALL = _('match all records. If other filters are specified, they will be '
             'applied. This option is only useful when you need to explicitly '
             'request that no filters be applied.')

# General Resource
OPTION_NAME = PulpCliOption('--display-name', DESC_NAME, required=False)
OPTION_DESCRIPTION = PulpCliOption('--description', DESC_DESCRIPTION, required=False)
OPTION_NOTES = PulpCliOption('--note', DESC_NOTE, required=False,
                             allow_multiple=True, parse_func=parsers.parse_notes)

# IDs
OPTION_REPO_ID = PulpCliOption('--repo-id', DESC_ID_ALLOWING_DOTS, required=True,
                               validate_func=validators.id_validator_allow_dots)
OPTION_GROUP_ID = PulpCliOption('--group-id', DESC_ID, required=True,
                                validate_func=validators.id_validator)
OPTION_CONSUMER_ID = PulpCliOption('--consumer-id', DESC_ID_ALLOWING_DOTS, required=True,
                                   validate_func=validators.id_validator_allow_dots)

FLAG_ALL = PulpCliFlag('--all', DESC_ALL)
