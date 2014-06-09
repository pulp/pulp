"""
This module contains management functions for the models found in the
pulp.server.db.model.resources module.
"""
from gettext import gettext as _
import pymongo
import random

from pulp.server.db.model import criteria, resources
from pulp.server import exceptions


def filter_workers(criteria):
    """
    Return Worker objects that match the given criteria

    :param criteria: A Criteria containing a query to be used to find Worker objects
    :type  criteria: pulp.server.db.model.criteria.Criteria
    :return:         A generator that iterates over the result set
    :rtype:          generator
    """
    workers = resources.Worker.get_collection().query(criteria)
    for w in workers:
        yield resources.Worker.from_bson(w)


def get_least_busy_worker():
    """
    Return the Worker instance with the lowest num_reservations. This function makes no
    guarantees about which Worker gets returned in the event of a tie.

    :returns: The Worker instance with the lowest num_reservations.
    :rtype:   pulp.server.db.model.resources.Worker
    """
    # Build a mapping of queue names to number of reservations against them
    workers = filter_workers(criteria.Criteria())
    reservation_map = {}
    for worker in workers:
        reservation_map[worker.queue_name] = {'num_reservations': 0, 'worker': worker}
    if not reservation_map:
        raise exceptions.NoWorkers()

    for reserved_resource in resources.ReservedResource.get_collection().find():
        if reserved_resource['assigned_queue'] in reservation_map:
            reservation_map[reserved_resource['assigned_queue']]['num_reservations'] += \
                reserved_resource['num_reservations']

    # Now let's flatten the reservation map into a list of 3-tuples, where the first element
    # is the num_reservations on the queue, the second element is a pseudorandom tie-breaker, and
    # the third is the worker. This will be easy to sort and get the least busy worker
    results = [
        (v['num_reservations'], random.random(), v['worker']) for k, v in reservation_map.items()]
    results.sort()

    # Since results is sorted by least busy worker, we can just return the first one
    return results[0][2]


def get_or_create_reserved_resource(name):
    """
    Get or create a ReservedResource instance with the given name. If the object is created,
    initialize its num_reservations attribute to 1, and set its assigned_queue to None.

    :param name: The name of the resource that the ReservedResource tracks
    :type  name: basestring
    :return:     A ReservedResource instance for the given name
    :rtype:      pulp.server.db.model.resources.ReservedResource
    """
    reserved_resource = resources.ReservedResource.get_collection().find_and_modify(
        query={'_id': name},
        update={'$setOnInsert': {'num_reservations': 1, 'assigned_queue': None}},
        upsert=True, new=True)
    return resources.ReservedResource(
        name=reserved_resource['_id'], assigned_queue=reserved_resource['assigned_queue'],
        num_reservations=reserved_resource['num_reservations'])
