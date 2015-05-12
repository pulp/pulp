from pulp.common import dateutils
from pulp.plugins.model import Repository


def to_transfer_repo(repo_data):
    """
    Converts the given database representation of a repository into a plugin
    repository transfer object, including any other fields that need to be
    included.

    @param repo_data: database representation of a repository
    @type  repo_data: dict

    @return: transfer object used in many plugin API calls
    @rtype:  pulp.plugins.model.Repository}
    """
    r = Repository(repo_data['id'], repo_data['display_name'], repo_data['description'],
                   repo_data['notes'], content_unit_counts=repo_data['content_unit_counts'],
                   last_unit_added=_ensure_tz_specified(repo_data.get('last_unit_added')),
                   last_unit_removed=_ensure_tz_specified(repo_data.get('last_unit_removed')))
    return r


def _ensure_tz_specified(time_stamp):
    """
    Check a datetime that came from the database to ensure it has a timezone specified in UTC
    Mongo doesn't include the TZ info so if no TZ is set this assumes UTC.

    :param time_stamp: a datetime object to ensure has UTC tzinfo specified
    :type time_stamp: datetime.datetime
    :return: The time_stamp with a timezone specified
    :rtype: datetime.datetime
    """
    if time_stamp:
            time_stamp = dateutils.to_utc_datetime(time_stamp, no_tz_equals_local_tz=False)
    return time_stamp
