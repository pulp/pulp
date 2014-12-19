"""
The way tasks with reservations are dispatched changed in  the 2.6 release. If Pulp services are
stopped while a task is executing, the task_status and reserved_resources collections will have
stale data. This migration updates all task_status documents with 'RUNNING' or 'WAITING' state to
'CANCELED' state. This migration also deletes all documents in the reserved_resources collection.
"""
from pulp.common.constants import CALL_CANCELED_STATE, CALL_INCOMPLETE_STATES
from pulp.server.db import connection


def migrate(*args, **kwargs):
    """
    Mark all tasks in incomplete state as canceled and remove all reserved resources documents.

    :param args:   Unused
    :type  args:   list
    :param kwargs: Unused
    :type  kwargs: dict
    """
    _migrate_task_status()
    _migrate_reserved_resources()


def _migrate_task_status():
    """
    Find all task_status documents in an incomplete state and set the state to canceled.
    """
    task_status = connection.get_collection('task_status')
    task_status.update({'state': {'$in': CALL_INCOMPLETE_STATES}},
                       {'$set': {'state': CALL_CANCELED_STATE}}, multi=True)


def _migrate_reserved_resources():
    """
    Remove all documents from the reserved_resources collection.
    """
    reserved_resources = connection.get_collection('reserved_resources')
    reserved_resources.remove({})
