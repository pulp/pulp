"""
This migration deletes the archived_calls collection if it is present.
"""
from gettext import gettext as _
import logging

from pulp.server.db import connection

_logger = logging.getLogger(__name__)


def migrate(*args, **kwargs):
    """
    Perform the migration as described in this module's docblock.

    :param args:   unused
    :type  args:   list
    :param kwargs: unused
    :type  kwargs: dict
    """
    db = connection.get_database()
    # If 'archived_calls' is not present, do nothing.
    if 'archived_calls' not in db.collection_names():
        return

    # If it's present, drop it
    collection = db['archived_calls']
    collection.drop()
    msg = _("Deleted the archived_calls collection.")
    _logger.info(msg)
