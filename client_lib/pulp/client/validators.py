"""
Methods in this module are meant to be passed to Okaara's validator function.
As such, all methods have no return value. An exception will be raised if
validation fails. See the parsers module if a return value is desired.
"""

import re
from gettext import gettext as _

from pulp.common import dateutils
from pulp.common.plugins import importer_constants


ID_REGEX_ALLOW_DOTS = re.compile(r'^[.\-_A-Za-z0-9]+$')
ID_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$')


def positive_int_validator(x):
    """
    Validates that the input is a positive integer.

    :param x: input value to be validated
    :type  x: int

    :raise ValueError: if the input is not a positive integer
    """
    if int(x) <= 0:
        raise ValueError(_('value must be greater than 0'))


def non_negative_int_validator(x):
    """
    Validates that the input is a non-negative integer.

    :param x: input value to be validated
    :type  x: int

    :raise ValueError: if the input is not a non-negative integer
    """
    if int(x) < 0:
        raise ValueError(_('value must not be negative'))


def iso8601_datetime_validator(x):
    """
    Validates that a user-entered value is a correct iso8601 date

    :param x: input value to be validated
    :type x: str

    :raise ValueError: if the input is not a valid iso8601 string
    """
    try:
        dateutils.parse_iso8601_datetime(x)
    except Exception:
        raise ValueError(_('value must be a valid iso8601 string (yyyy-mm-ddThh:mm:ssZ)'))


def interval_iso6801_validator(x):
    """
    Validates that a user-entered value is a correct iso8601 date with
    an interval.

    :param x: input value to be validated
    :type  x: str

    :raise ValueError: if the input is not a valid iso8601 string
    """

    # These are meant to be used with okaara which expects either ValueError or
    # TypeError for a graceful failure, so catch any parsing errors and raise
    # the appropriate new error.
    try:
        dateutils.parse_iso8601_interval(x)
    except Exception:
        raise ValueError(_('value must be a valid iso8601 string with an interval'))


def id_validator(x):
    """
    Validates that the input is a valid Pulp ID. This validator can be used on
    either a single ID or a list of IDs, the latter occuring in the event that
    allow_multiple is set to True for the option.

    :param x: input value to be validated
    :type  x: str or list

    :raise ValueError: if the input is not a valid ID or any entry in the list
           of IDs is invalid
    """
    if not isinstance(x, (list, tuple)):
        x = [x]

    for input_id in x:
        if ID_REGEX.match(input_id) is None:
            raise ValueError(_('value must contain only letters, numbers, underscores, and '
                               'hyphens'))


def id_validator_allow_dots(x):
    """
    Validates that the input is a valid Pulp ID. This validator also allows
    dots or periods in the id. This validator can be used on either a single ID
    or a list of IDs, the latter occuring in the event that
    allow_multiple is set to True for the option.

    :param x: input value to be validated
    :type  x: str or list

    :raise ValueError: if the input is not a valid ID or any entry in the list
           of IDs is invalid
    """
    if not isinstance(x, (list, tuple)):
        x = [x]

    for input_id in x:
        if ID_REGEX_ALLOW_DOTS.match(input_id) is None:
            raise ValueError(_('value must contain only letters, numbers, underscores, periods and '
                               'hyphens'))


def download_policy_validator(x):
    """
    Download policy validator.

    :param x: input value to be validated
    :type  x: str or list

    :raise ValueError: if the input is not a valid policy.
    """
    valid = (
        importer_constants.DOWNLOAD_IMMEDIATE,
        importer_constants.DOWNLOAD_BACKGROUND,
        importer_constants.DOWNLOAD_ON_DEMAND)
    if x not in valid:
        raise ValueError(_('policy must be: ({p})'.format(p=' | '.join(valid))))
