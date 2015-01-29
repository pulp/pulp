"""
This defines custom fields to be stored in the database.

Each field class is inherited from one or more mongoengine fields
and it provides it's own validation code.
"""

from isodate import ISO8601Error
from mongoengine import StringField

from pulp.common import dateutils


class ISO8601StringField(StringField):
    """
    This represents a string which is an ISO8601 representation of datetime.datetime.
    """
    def __init__(self, **kwargs):
        super(ISO8601StringField, self).__init__(**kwargs)

    def validate(self, value):
        super(ISO8601StringField, self).validate(value)

        try:
            dateutils.parse_iso8601_datetime(value)
        except ISO8601Error, e:
            self.error(e.message)
