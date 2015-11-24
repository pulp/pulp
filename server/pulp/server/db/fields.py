"""
This defines custom fields to be stored in the database.

Each field class is inherited from one or more mongoengine fields
and it provides it's own validation code.
"""

from isodate import ISO8601Error
from mongoengine import StringField, DateTimeField

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
            self.error(str(e))


class UTCDateTimeField(DateTimeField):
    """
    Any datetime value retrived from this field will have its timezone set to UTC. It is otherwise
    identical to the mongoengine DateTimeField. It can replace the mongoengine DateTimeField without
    need for a database migration.
    """

    def to_python(self, value):
        """
        Ensures that the datetime object returned has timezone UTC set. This assumes that if the
        value lacks a timezone, the data is already UTC, and the corresponding timezone object
        will be added.

        :param value: a datetime object
        :type  value: datetime.datetime

        :return: an equivalent datetime object with the timezone set to UTC
        :rtype:  datetime.datetime
        """
        ret = super(UTCDateTimeField, self).to_python(value)
        return dateutils.ensure_tz(ret)
