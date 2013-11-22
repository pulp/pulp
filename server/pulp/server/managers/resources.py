# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
"""
This module contains management functions for the models found in the
pulp.server.db.model.resources module.
"""
from gettext import gettext as _
import pymongo

from pulp.server.db.model import resources


def filter_available_queues(criteria):
    """
    Return AvailableQueue objects that match the given criteria

    :param criteria: A Criteria containing a query to be used to find AvailableQueue objects
    :type  criteria: pulp.server.db.model.criteria.Criteria
    """
    available_queues = resources.AvailableQueue.get_collection().query(criteria)
    for q in available_queues:
        yield resources.AvailableQueue(name=q['_id'],
                                       num_reservations=q['num_reservations'])


def get_least_busy_available_queue():
    """
    Return the AvailableQueue instance with the lowest num_reservations. This function makes no
    guarantees about which AvailableQueue gets returned in the event of a tie.

    :returns: The AvailableQueue instance with the lowest num_reservations.
    :rtype:   pulp.server.db.model.resources.AvailableQueue
    """
    available_queue = resources.AvailableQueue.get_collection().find_one(
        sort=[('num_reservations', pymongo.ASCENDING)])

    if available_queue is None:
        msg = _('There are no available queues in the system for reserved task work.')
        raise NoAvailableQueues(msg)

    return resources.AvailableQueue(name=available_queue['_id'],
                                    num_reservations=available_queue['num_reservations'])


def get_or_create_available_queue(name):
    """
    Get or create an AvailableQueue object with the given name. If the object is created, initialize
    its num_reservations attribute to 0.

    :param name: The name of the requested AvailableQueue
    :type  name: basestring
    :return:     An AvailableQueue object for the given name
    :rtype:      pulp.server.db.model.resources.AvailableQueue
    """
    available_queue = resources.AvailableQueue.get_collection().find_and_modify(
        query={'_id': name}, update={'$setOnInsert': {'num_reservations': 0}},
        upsert=True, new=True)
    return resources.AvailableQueue(name=available_queue['_id'],
                                    num_reservations=available_queue['num_reservations'])


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


class NoAvailableQueues(Exception):
    """ 
    This Exception is raised by _get_least_busy_available_queue() if there are no AvailableQueue
    objects.
    """
    pass
