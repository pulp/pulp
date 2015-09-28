"""
This defines custom fields to be stored in the database.

Each field class is inherited from one or more mongoengine fields
and it provides it's own validation code.
"""

import hashlib

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
            self.error(str(e))


class ChecksumField(StringField):
    """
    A checksum field that encodes the algorithm and hash
    using the format of: <algorithm>:<digest>.
    """

    ALGORITHMS = hashlib.algorithms

    def validate(self, value):
        if not value:
            return
        parts = value.split(':', 1)
        if len(parts) == 2:
            algorithm = parts[0].lower()
            if algorithm not in self.ALGORITHMS:
                raise ValueError('algorithm must be: %s' % str(self.ALGORITHMS))
            digest = parts[1]
            if len(digest) < 1:
                raise ValueError('digest not specified')
        else:
            raise ValueError('must be: <algorithm>:<digest>')
