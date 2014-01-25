# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server import exceptions
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.db.model.repository import RepoImporter, RepoDistributor
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.schedule import utils
from pulp.server.tasks.repository import sync_with_auto_publish, publish


_PUBLISH_OPTION_KEYS = ('override_config',)
_SYNC_OPTION_KEYS = ('override_config',)


class RepoSyncScheduleManager(object):
    @classmethod
    def list(cls, repo_id, importer_id):
        """
        Returns an iterator of ScheduledCall instances that represent schedules
        for the specified repo and importer.

        :param repo_id:     unique ID for a repository
        :type  repo_id:     basestring
        :param importer_id: unique ID for an importer
        :type  importer_id: basestring

        :return:    iterator of ScheduledCall instances
        :rtype:     iterator
        """
        cls.validate_importer(repo_id, importer_id)

        return utils.get_by_resource(RepoImporter.build_resource_tag(repo_id, importer_id))

    @classmethod
    def create(cls, repo_id, importer_id, sync_options, schedule,
               failure_threshold=None, enabled=True):
        """
        Create a new sync schedule for a given repository using the given importer.

        :param repo_id:         unique ID for a repository
        :type  repo_id:         basestring
        :param importer_id:     unique ID for an importer
        :type  importer_id:     basestring
        :param sync_options:    dictionary that contains the key 'override_config',
                                whose value should be passed as the 'overrides'
                                parameter to the sync task. This wasn't originally
                                documented, so it isn't clear why overrides value
                                couldn't be passed directly.
        :type  sync_options:    dict
        :param schedule_data:   dictionary that contains the key 'schedule', whose
                                value is an ISO8601 string. This wasn't originally
                                documented, so it isn't clear why the string itself
                                couldn't have been passed directly.
        :type  schedule_data:   dict

        :return:    new schedule instance
        :rtype:     pulp.server.db.model.dispatch.ScheduledCall
        """
        # validate the input
        cls.validate_importer(repo_id, importer_id)
        utils.validate_keys(sync_options, _SYNC_OPTION_KEYS)
        utils.validate_initial_schedule_options(schedule, failure_threshold, enabled)

        task = sync_with_auto_publish.name
        args = [repo_id]
        kwargs = {'overrides': sync_options['override_config']}
        resource = RepoImporter.build_resource_tag(repo_id, importer_id)
        schedule = ScheduledCall(schedule, task, args=args, kwargs=kwargs,
                                 resource=resource, failure_threshold=failure_threshold,
                                 enabled=enabled)
        schedule.save()
        try:
            cls.validate_importer(repo_id, importer_id)
        except exceptions.MissingResource:
            # back out of this whole thing, since the importer disappeared
            utils.delete(schedule.id)
            raise

        return schedule

    @classmethod
    def update(cls, repo_id, importer_id, schedule_id, updates):
        """
        Update an existing sync schedule.

        :param repo_id:         unique ID for a repository
        :type  repo_id:         basestring
        :param importer_id:     unique ID for an importer
        :type  importer_id:     basestring
        :param schedule_id:     unique ID for a schedule
        :type  schedule_id:     basestring
        :param updates:         dictionary of updates to apply
        :type  updates:         dict

        :return ScheduledCall instance as it appears after the update
        :rtype  pulp.server.db.model.dispatch.ScheduledCall
        """
        cls.validate_importer(repo_id, importer_id)

        # legacy logic that can't be explained
        if 'override_config' in updates:
            updates['kwargs'] = {'overrides': updates.pop('override_config')}

        utils.validate_updated_schedule_options(updates)

        return utils.update(schedule_id, updates)

    @classmethod
    def delete(cls, repo_id, importer_id, schedule_id):
        """
        Delete a scheduled sync from a given repository and importer.

        :param repo_id:         unique ID for a repository
        :type  repo_id:         basestring
        :param importer_id:     unique ID for an importer
        :type  importer_id:     basestring
        :param schedule_id:     unique ID for a schedule
        :type  schedule_id:     basestring
        """
        # validate the input
        cls.validate_importer(repo_id, importer_id)

        # remove from the scheduler
        utils.delete(schedule_id)

    @staticmethod
    def delete_by_importer_id(repo_id, importer_id):
        """
        Delete all schedules for the specified repo and importer.

        :param importer_id:     unique ID for an importer
        :type  importer_id:     basestring
        """
        utils.delete_by_resource(RepoImporter.build_resource_tag(repo_id, importer_id))

    @staticmethod
    def validate_importer(repo_id, importer_id):
        """
        Validate that the importer exists for the specified repo

        :param repo_id:         unique ID for a repository
        :type  repo_id:         basestring
        :param importer_id:     unique ID for an importer
        :type  importer_id:     basestring

        :raise: pulp.server.exceptions.MissingResource
        """
        # make sure the passed in importer id matches the current importer on the repo
        importer_manager = managers_factory.repo_importer_manager()
        importer = importer_manager.get_importer(repo_id)
        if importer_id != importer['id']:
            raise exceptions.MissingResource(importer=importer_id)


class RepoPublishScheduleManager(object):
    @classmethod
    def list(cls, repo_id, distributor_id):
        """
        Returns an iterator of ScheduledCall instances that represent schedules
        for the specified repo and distributor.

        :param repo_id:         unique ID for a repository
        :type  repo_id:         basestring
        :param distributor_id:  unique ID for an distributor
        :type  distributor_id:  basestring

        :return:    iterator of ScheduledCall instances
        :rtype:     iterator
        """
        cls.validate_distributor(repo_id, distributor_id)

        return utils.get_by_resource(RepoDistributor.build_resource_tag(repo_id, distributor_id))

    @classmethod
    def create(cls, repo_id, distributor_id, publish_options, schedule,
               failure_threshold=None, enabled=True):
        """
        Create a new scheduled publish for the given repository and distributor.

        :param repo_id:         unique ID for a repository
        :type  repo_id:         basestring
        :param distributor_id:  unique ID for an distributor
        :type  distributor_id:  basestring
        :param publish_options: dictionary that contains the key 'override_config',
                                whose value should be passed as the 'overrides'
                                parameter to the publish task. This wasn't originally
                                documented, so it isn't clear why overrides value
                                couldn't be passed directly.
        :type  sync_options:    dict
        :param schedule_data:   dictionary that contains the key 'schedule', whose
                                value is an ISO8601 string. This wasn't originally
                                documented, so it isn't clear why the string itself
                                couldn't have been passed directly.
        :type  schedule_data:   dict

        :return:    new schedule instance
        :rtype:     pulp.server.db.model.dispatch.ScheduledCall
        """
        # validate the input
        cls.validate_distributor(repo_id, distributor_id)
        utils.validate_keys(publish_options, _PUBLISH_OPTION_KEYS)
        utils.validate_initial_schedule_options(schedule, failure_threshold, enabled)

        task = publish.name
        args = [repo_id, distributor_id]
        kwargs = {'overrides': publish_options['override_config']}
        resource = RepoDistributor.build_resource_tag(repo_id, distributor_id)
        schedule = ScheduledCall(schedule, task, args=args, kwargs=kwargs,
                                 resource=resource, failure_threshold=failure_threshold,
                                 enabled=enabled)
        schedule.save()

        try:
            cls.validate_distributor(repo_id, distributor_id)
        except exceptions.MissingResource:
            # back out of this whole thing, since the distributor disappeared
            utils.delete(schedule.id)
            raise

        return schedule

    @classmethod
    def update(cls, repo_id, distributor_id, schedule_id, updates):
        """
        Update an existing scheduled publish for the given repository and distributor.

        :param repo_id:         unique ID for a repository
        :type  repo_id:         basestring
        :param distributor_id:  unique ID for a distributor
        :type  distributor_id:  basestring
        :param schedule_id:     unique ID for a schedule
        :type  schedule_id:     basestring
        :param updates:         dictionary of updates to apply
        :type  updates:         dict

        :return ScheduledCall instance as it appears after the update
        :rtype  pulp.server.db.model.dispatch.ScheduledCall
        """

        cls.validate_distributor(repo_id, distributor_id)
        if 'override_config' in updates:
            updates['kwargs'] = {'overrides': updates.pop('override_config')}

        utils.validate_updated_schedule_options(updates)

        return utils.update(schedule_id, updates)

    @classmethod
    def delete(cls, repo_id, distributor_id, schedule_id):
        """
        Delete an existing scheduled publish from the given repository and distributor.

        :param repo_id:         unique ID for a repository
        :type  repo_id:         basestring
        :param distributor_id:  unique ID for a distributor
        :type  distributor_id:  basestring
        :param schedule_id:     unique ID for a schedule
        :type  schedule_id:     basestring
        """
        # validate the input
        cls.validate_distributor(repo_id, distributor_id)

        # remove from the scheduler
        utils.delete(schedule_id)

    @staticmethod
    def delete_by_distributor_id(repo_id, distributor_id):
        """
        Delete all schedules for the specified repo and distributor.

        :param distributor_id:  unique ID for an distributor
        :type  distributor_id:  basestring
        """
        utils.delete_by_resource(RepoDistributor.build_resource_tag(repo_id, distributor_id))

    @staticmethod
    def validate_distributor(repo_id, distributor_id):
        """
        Validate that the distributor exists for the specified repo

        :param repo_id:         unique ID for a repository
        :type  repo_id:         basestring
        :param distributor_id:  unique ID for a distributor
        :type  distributor_id:  basestring

        :raise: pulp.server.exceptions.MissingResource
        """
        distributor_manager = managers_factory.repo_distributor_manager()
        distributor_manager.get_distributor(repo_id, distributor_id)
