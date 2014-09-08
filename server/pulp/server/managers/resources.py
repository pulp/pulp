"""
This module contains management functions for the models found in the
pulp.server.db.model.resources module.
"""

from pulp.server.db.model import criteria, resources


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


def get_worker_for_reservation(resource_id):
    """
    Return the Worker instance that is associated with a reservation of type resource_id. If
    there are no workers with that reservation_id type return None.

    :param resource_id:    The name of the resource you wish to reserve for your task.
    :type resource_id:     basestring
    :returns:              The Worker instance that has a reserved_resource entry of type
                           `resource_id` associated with it or None.
    :rtype:                pulp.server.db.model.resources.Worker
    """
    reservation = resources.ReservedResource.get_collection().find_one({'resource_id': resource_id})
    if reservation:
        find_worker_by_name = criteria.Criteria({'_id': reservation['worker_name']})
        worker_bson = resources.Worker.get_collection().query(find_worker_by_name)[0]
        return resources.Worker.from_bson(worker_bson)
    else:
        return None


def get_unreserved_worker():
    """
    Return the Worker instance that has no reserved_resource entries associated with it. If there
    are no unreserved workers return None.

    :returns: The Worker instance that has no reserved_resource entries associated with it or None.
    :rtype:   pulp.server.db.model.resources.Worker
    """
    # Build a mapping of queue names to Worker objects
    workers_dict = dict((worker['name'], worker) for worker in filter_workers(criteria.Criteria()))
    worker_names = [name for name in workers_dict.keys()]
    reserved_names = [r['worker_name'] for r in resources.ReservedResource.get_collection().find()]

    # Find an unreserved worker using set differences of the names
    unreserved_workers = set(worker_names) - set(reserved_names)
    try:
        return workers_dict[unreserved_workers.pop()]
    except KeyError:
        # All workers are reserved
        return
