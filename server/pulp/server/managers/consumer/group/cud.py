# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import logging
import re

from celery import task
from pymongo.errors import DuplicateKeyError

from pulp.server import exceptions as pulp_exceptions
from pulp.common import error_codes
from pulp.server.async.tasks import Task, TaskResult
from pulp.server.db.model.consumer import Consumer, ConsumerGroup
from pulp.server.exceptions import PulpCodedException, PulpException
from pulp.server.managers import factory as manager_factory
from pulp.server.tasks.consumer import bind as bind_task, unbind as unbind_task

logger = logging.getLogger(__name__)

_CONSUMER_GROUP_ID_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen


class ConsumerGroupManager(object):
    @staticmethod
    def create_consumer_group(group_id, display_name=None, description=None, consumer_ids=None,
                              notes=None):
        """
        Create a new consumer group.

        :param group_id:     unique id of the consumer group
        :type  group_id:     str
        :param display_name: display name of the consumer group
        :type  display_name: str or None
        :param description:  description of the consumer group
        :type  description:  str or None
        :param consumer_ids: list of ids for consumers initially belonging to the consumer group
        :type  consumer_ids: list or None
        :param notes:        notes for the consumer group
        :type  notes:        dict or None
        :return:             SON representation of the consumer group
        :rtype:              bson.SON
        """
        validation_errors = []
        if group_id is None:
            validation_errors.append(PulpCodedException(error_codes.PLP1002, field='group_id'))
        elif _CONSUMER_GROUP_ID_REGEX.match(group_id) is None:
            validation_errors.append(PulpCodedException(error_codes.PLP1003, field='group_id'))

        if consumer_ids:
            # Validate that all the consumer_ids exist and raise an exception if they don't
            consumer_collection = Consumer.get_collection()
            matched_consumers = consumer_collection.find({'id': {'$in': consumer_ids}})
            if matched_consumers.count() is not len(consumer_ids):
                # Create a set of all the matched consumer_ids
                matched_consumers_set = set()
                for consumer in matched_consumers:
                    matched_consumers_set.add(consumer.get('id'))
                # find the missing items
                for consumer_id in (set(consumer_ids)).difference(matched_consumers_set):
                    validation_errors.append(PulpCodedException(error_codes.PLP1001,
                                                                consumer_id=consumer_id))

        if validation_errors:
            raise pulp_exceptions.PulpCodedValidationException(validation_errors)

        collection = ConsumerGroup.get_collection()
        consumer_group = ConsumerGroup(group_id, display_name, description, consumer_ids, notes)
        try:
            collection.insert(consumer_group, safe=True)
        except DuplicateKeyError:
            raise pulp_exceptions.PulpCodedValidationException(
                [PulpCodedException(error_codes.PLP1004, type=ConsumerGroup.collection_name,
                                    object_id=group_id)])

        group = collection.find_one({'id': group_id})
        return group

    @staticmethod
    def update_consumer_group(group_id, **updates):
        """
        Update an existing consumer group.
        Valid keyword arguments are:
         * display_name
         * description
         * notes

        For notes, provide a dict with key:value pairs for changes only. It is
        not necessary to provide the entire field value. If a value is empty or
        otherwise evaluates to False, that key will be unset.

        @param group_id: unique id of the consumer group to update
        @type group_id: str
        @param updates: keyword arguments of attributes to update
        @return: SON representation of the updated consumer group
        @rtype:  L{bson.SON}
        """
        collection = validate_existing_consumer_group(group_id)
        keywords = updates.keys()
        # validate keywords
        valid_keywords = set(('display_name', 'description', 'notes'))
        invalid_keywords = set(keywords) - valid_keywords
        if invalid_keywords:
            raise pulp_exceptions.InvalidValue(list(invalid_keywords))

        # handle notes as a delta against the existing notes attribute
        notes = updates.pop('notes', None)
        if notes:
            unset_dict = {}
            for key, value in notes.iteritems():
                newkey = 'notes.%s' % key
                if value:
                    updates[newkey] = value
                else:
                    unset_dict[newkey] = value

            if unset_dict:
                collection.update({'id': group_id}, {'$unset': unset_dict},
                                  safe=True)

        if updates:
            collection.update({'id': group_id}, {'$set': updates}, safe=True)
        group = collection.find_one({'id': group_id})
        return group

    @staticmethod
    def delete_consumer_group(group_id):
        """
        Delete a consumer group.
        @param group_id: unique id of the consumer group to delete
        @type group_id: str
        """
        collection = validate_existing_consumer_group(group_id)
        # Delete from the database
        collection.remove({'id': group_id}, safe=True)

    def remove_consumer_from_groups(self, consumer_id, group_ids=None):
        """
        Remove a consumer from the list of consumer groups provided.
        If no consumer groups are specified, remove the consumer from all consumer groups
        its currently in.
        (idempotent: useful when deleting consumersitories)
        @param consumer_id: unique id of the consumer to remove from consumer groups
        @type  consumer_id: str
        @param group_ids: list of consumer group ids to remove the consumer from
        @type  group_ids: list of None
        """
        spec = {}
        if group_ids is not None:
            spec = {'id': {'$in': group_ids}}
        collection = ConsumerGroup.get_collection()
        collection.update(spec, {'$pull': {'consumer_ids': consumer_id}}, multi=True, safe=True)

    @staticmethod
    def associate(group_id, criteria):
        """
        Associate a set of consumers, that match the passed in criteria, to a consumer group.
        @param group_id: unique id of the group to associate consumers to
        @type  group_id: str
        @param criteria: Criteria instance representing the set of consumers to associate
        @type  criteria: L{pulp.server.db.model.criteria.Criteria}
        """
        group_collection = validate_existing_consumer_group(group_id)
        consumer_collection = Consumer.get_collection()
        cursor = consumer_collection.query(criteria)
        consumer_ids = [r['id'] for r in cursor]
        if consumer_ids:
            group_collection.update(
                {'id': group_id},
                {'$addToSet': {'consumer_ids': {'$each': consumer_ids}}},
                safe=True)

    @staticmethod
    def unassociate(group_id, criteria):
        """
        Unassociate a set of consumers, that match the passed in criteria, from a consumer group.
        @param group_id: unique id of the group to unassociate consumers from
        @type  group_id: str
        @param criteria: Criteria specifying the set of consumers to unassociate
        @type  criteria: L{pulp.server.db.model.criteria.Criteria}
        """
        group_collection = validate_existing_consumer_group(group_id)
        consumer_collection = Consumer.get_collection()
        cursor = consumer_collection.query(criteria)
        consumer_ids = [r['id'] for r in cursor]
        if consumer_ids:
            group_collection.update(
                {'id': group_id},
                {'$pullAll': {'consumer_ids': consumer_ids}},
                safe=True)

    def add_notes(self, group_id, notes):
        """
        Add a set of notes to a consumer group.
        @param group_id: unique id of the group to add notes to
        @type  group_id: str
        @param notes: notes to add to the consumer group
        @type  notes: dict
        """
        group_collection = validate_existing_consumer_group(group_id)
        set_doc = dict(('notes.' + k, v) for k, v in notes.items())
        group_collection.update({'id': group_id}, {'$set': set_doc}, safe=True)

    def remove_notes(self, group_id, keys):
        """
        Remove a set of notes from a consumer group.
        @param group_id: unique id of the group to remove notes from
        @type  group_id: str
        @param keys: list of note keys to remove
        @type  keys: list
        """
        group_collection = validate_existing_consumer_group(group_id)
        unset_doc = dict(('notes.' + k, 1) for k in keys)
        group_collection.update({'id': group_id}, {'$unset': unset_doc}, safe=True)

    def set_note(self, group_id, key, value):
        """
        Set a single key and value pair in a consumer group's notes.
        @param group_id: unique id of the consumer group to set a note on
        @type  group_id: str
        @param key: note key
        @type  key: immutable
        @param value: note value
        """
        self.add_notes(group_id, {key: value})

    def unset_note(self, group_id, key):
        """
        Unset a single key and value pair in a consumer group's notes.
        @param group_id: unique id of the consumer group to unset a note on
        @type  group_id: str
        @param key: note key
        @type  key: immutable
        """
        self.remove_notes(group_id, [key])

    # content ------------------------------------------------------------

    @staticmethod
    def install_content(consumer_group_id, units, options):
        """
        Create an itinerary for consumer group content installation.
        :param consumer_group_id: unique id of the consumer group
        :type consumer_group_id: str
        :param units: units to install
        :type units: list or tuple
        :param options: options to pass to the install manager
        :type options: dict or None
        :return: Details of the subtasks that were executed
        :rtype: TaskResult
        """
        consumer_group = manager_factory.consumer_group_query_manager().get_group(consumer_group_id)
        agent_manager = manager_factory.consumer_agent_manager()

        return ConsumerGroupManager.process_group(consumer_group, error_codes.PLP0020,
                                                  {'group_id': consumer_group_id},
                                                  agent_manager.install_content, units, options)

    @staticmethod
    def update_content(consumer_group_id, units, options):
        """
        Create an itinerary for consumer group content update.
        :param consumer_group_id: unique id of the consumer group
        :type consumer_group_id: str
        :param units: units to update
        :type units: list or tuple
        :param options: options to pass to the update manager
        :type options: dict or None
        :return: Details of the subtasks that were executed
        :rtype: TaskResult
        """
        consumer_group = manager_factory.consumer_group_query_manager().get_group(consumer_group_id)
        agent_manager = manager_factory.consumer_agent_manager()

        return ConsumerGroupManager.process_group(consumer_group, error_codes.PLP0021,
                                                  {'group_id': consumer_group_id},
                                                  agent_manager.update_content, units, options)

    @staticmethod
    def uninstall_content(consumer_group_id, units, options):
        """
        Create an itinerary for consumer group content uninstallation.
        :param consumer_group_id: unique id of the consumer group
        :type consumer_group_id: str
        :param units: units to uninstall
        :type units: list or tuple
        :param options: options to pass to the uninstall manager
        :type options: dict or None
        :return: Details of the subtasks that were executed
        :rtype: TaskResult
        """
        consumer_group = manager_factory.consumer_group_query_manager().get_group(consumer_group_id)
        agent_manager = manager_factory.consumer_agent_manager()

        return ConsumerGroupManager.process_group(consumer_group, error_codes.PLP0022,
                                                  {'group_id': consumer_group_id},
                                                  agent_manager.uninstall_content, units, options)

    @staticmethod
    def bind(group_id, repo_id, distributor_id, notify_agent, binding_config, agent_options):
        """
        Bind the members of the specified consumer group.
        :param group_id: A consumer group ID.
        :type group_id: str
        :param repo_id: A repository ID.
        :type repo_id: str
        :param distributor_id: A distributor ID.
        :type distributor_id: str
        :param agent_options: Bind options passed to the agent handler.
        :type agent_options: dict
        :param notify_agent: indicates if the agent should be sent a message about the new binding
        :type  notify_agent: bool
        :param binding_config: configuration options to use when generating the payload for this binding
        :type binding_config: dict
        :return: Details of the subtasks that were executed
        :rtype: TaskResult
        """
        manager = manager_factory.consumer_group_query_manager()
        group = manager.get_group(group_id)

        bind_errors = []
        additional_tasks = []

        for consumer_id in group['consumer_ids']:
            try:
                report = bind_task(consumer_id, repo_id, distributor_id, notify_agent, binding_config,
                                   agent_options)
                if report.spawned_tasks:
                    additional_tasks.extend(report.spawned_tasks)
            except PulpException, e:
                # Log a message so that we can debug but don't throw
                logger.debug(e.message)
                bind_errors.append(e)
            except Exception, e:
                logger.exception(e.message)
                # Don't do anything else since we still want to process all the other consumers
                bind_errors.append(e)

        bind_error = None
        if len(bind_errors) > 0:
            bind_error = PulpCodedException(error_codes.PLP0004,
                                            repo_id=repo_id,
                                            distributor_id=distributor_id,
                                            group_id=group_id)
            bind_error.child_exceptions = bind_errors

        return TaskResult(error=bind_error, spawned_tasks=additional_tasks)

    @staticmethod
    def unbind(group_id, repo_id, distributor_id, options):
        """
        Unbind the members of the specified consumer group.
        :param group_id: A consumer group ID.
        :type group_id: str
        :param repo_id: A repository ID.
        :type repo_id: str
        :param distributor_id: A distributor ID.
        :type distributor_id: str
        :param options: Bind options passed to the agent handler.
        :type options: dict
        :return: TaskResult containing the ids of all the spawned tasks & bind errors
        :rtype: TaskResult
        """
        manager = manager_factory.consumer_group_query_manager()
        group = manager.get_group(group_id)

        bind_errors = []
        additional_tasks = []

        for consumer_id in group['consumer_ids']:
            try:
                report = unbind_task(consumer_id, repo_id, distributor_id, options)
                if report:
                    additional_tasks.extend(report.spawned_tasks)
            except PulpException, e:
                #Log a message so that we can debug but don't throw
                logger.warn(e.message)
                bind_errors.append(e)
            except Exception, e:
                bind_errors.append(e)
                #Don't do anything else since we still want to process all the other consumers

        bind_error = None
        if len(bind_errors) > 0:
            bind_error = PulpCodedException(error_codes.PLP0005,
                                            repo_id=repo_id,
                                            distributor_id=distributor_id,
                                            group_id=group_id)
            bind_error.child_exceptions = bind_errors
        return TaskResult(error=bind_error, spawned_tasks=additional_tasks)

    @staticmethod
    def process_group(consumer_group, error_code, error_kwargs, process_method, *args):
        """
        Process an action over a group of consumers

        :param consumer_group: A consumer group dictionary
        :type consumer_group: dict
        :param error_code: The error code to wrap any consumer failures in
        :type error_code: pulp.common.error_codes.Error
        :param error_kwargs: The keyword arguments to pass to the error code when it is instantiated
        :type error_kwargs: dict
        :param process_method: The method to call on each consumer in the group
        :type process_method: function
        :param args: any additional arguments passed to this method will be passed to the
                     process method function
        :type args: list of arguments
        :returns: A TaskResult with the overall results of the group
        :rtype: TaskResult
        """
        errors = []
        spawned_tasks = []
        for consumer_id in consumer_group['consumer_ids']:
            try:
                group_task = process_method(consumer_id, *args)
                spawned_tasks.append(group_task)
            except PulpException, e:
                #Log a message so that we can debug but don't throw
                logger.warn(e.message)
                errors.append(e)
            except Exception, e:
                logger.exception(e.message)
                errors.append(e)
                #Don't do anything else since we still want to process all the other consumers

        error = None
        if len(errors) > 0:
            error = PulpCodedException(error_code, **error_kwargs)
            error.child_exceptions = errors
        return TaskResult({}, error, spawned_tasks)


associate = task(ConsumerGroupManager.associate, base=Task, ignore_result=True)
create_consumer_group = task(ConsumerGroupManager.create_consumer_group, base=Task)
delete_consumer_group = task(ConsumerGroupManager.delete_consumer_group, base=Task,
                             ignore_result=True)
update_consumer_group = task(ConsumerGroupManager.update_consumer_group, base=Task)
unassociate = task(ConsumerGroupManager.unassociate, base=Task, ignore_result=True)
bind = task(ConsumerGroupManager.bind, base=Task)
unbind = task(ConsumerGroupManager.unbind, base=Task)


def validate_existing_consumer_group(group_id):
    """
    Validate the existence of a consumer group, given its id.
    Returns the consumer group db collection upon successful validation,
    raises an exception upon failure
    @param group_id: unique id of the consumer group to validate
    @type  group_id: str
    @return: consumer group db collection
    @rtype:  L{pulp.server.db.connection.PulpCollection}
    @raise:  L{pulp.server.exceptions.MissingResource}
    """
    collection = ConsumerGroup.get_collection()
    consumer_group = collection.find_one({'id': group_id})
    if consumer_group is not None:
        return collection
    raise pulp_exceptions.MissingResource(consumer_group=group_id)
