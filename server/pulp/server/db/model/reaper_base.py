from datetime import timedelta, datetime

from pulp.common import dateutils
from pulp.server.compat import ObjectId


class ReaperMixin(object):
    """
    A Mixin class providing default reaping functionality.

    This class is designed to be used as a Mixin on any Model object that needs to have its
    documents periodically reaped by the pulp reaper.
    """

    @classmethod
    def reap_old_documents(cls, config_days):
        """
        Remove documents from that are older than config_days.

        :param config_days: Remove all records older than the number of days set by config_days.
        :type config_days: float
        """
        age = timedelta(days=config_days)
        # Generate an ObjectId that we can use to know which objects to remove
        expired_object_id = _create_expired_object_id(age)
        # Remove all objects older than the timestamp encoded into the generated ObjectId
        collection = cls.get_collection()
        collection.remove({'_id': {'$lte': expired_object_id}})


def _create_expired_object_id(age):
    """
    By default, MongoDB uses a primary key that has the date that each document was created encoded
    into it. This method generates a pulp.server.compat.ObjectId that corresponds to the timstamp of
    now minus age, where age is a timedelta. For example, if age is 60 seconds, this will
    return an ObjectId that has the UTC time that it was 60 seconds ago encoded into it. This is
    useful in this module, as we want to automatically delete documents that are older than a
    particular age, and so we can issue a remove query to MongoDB for objects with _id attributes
    that are less than the ObjectId returned by this method.

    :param age: A timedelta representing the relative time in the past that you wish an ObjectId
                to be generated against.
    :type  age: datetime.timedelta
    :return:    An ObjectId containing the encoded time (now - age).
    :rtype:     pulp.server.compat.ObjectId
    """
    now = datetime.now(dateutils.utc_tz())
    expired_datetime = now - age
    expired_object_id = ObjectId.from_datetime(expired_datetime)
    return expired_object_id
