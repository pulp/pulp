# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
        cls.validate_importer(repo_id, importer_id)

        return utils.get_by_resource(RepoImporter.build_resource_tag(repo_id, importer_id))

    @classmethod
    def create(cls, repo_id, importer_id, sync_options, schedule_data):
        """
        Create a new sync schedule for a given repository using the given importer.

        :param repo_id:
        :param importer_id:
        :param sync_options:
        :param schedule_data:
        :return:    new schedule
        :rtype:     pulp.server.db.model.dispatch.ScheduledCall
        """
        # validate the input
        cls.validate_importer(repo_id, importer_id)
        utils.validate_keys(sync_options, _SYNC_OPTION_KEYS)

        utils.validate_initial_schedule_options(schedule_data)

        task = sync_with_auto_publish.name
        args = [repo_id]
        kwargs = {'overrides': sync_options['override_config']}
        resource = RepoImporter.build_resource_tag(repo_id, importer_id)
        schedule = ScheduledCall(schedule_data['schedule'], task, args=args,
                                 kwargs=kwargs, resource=resource)
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

        :param repo_id:
        :param importer_id:
        :param schedule_id:
        :param sync_options:
        :param schedule_data:
        :return:
        """
        cls.validate_importer(repo_id, importer_id)

        if 'override_config' in updates:
            updates['kwargs'] = {'overrides': updates.pop('override_config')}

        utils.validate_updated_schedule_options(updates)

        utils.update(schedule_id, updates)

    @classmethod
    def delete(cls, repo_id, importer_id, schedule_id):
        """
        Delete a scheduled sync from a given repository and importer.

        :param repo_id:
        :param importer_id:
        :param schedule_id:
        :return:
        """
        # validate the input
        cls.validate_importer(repo_id, importer_id)

        # remove from the scheduler
        utils.delete(schedule_id)

    @staticmethod
    def validate_importer(repo_id, importer_id):
        # make sure the passed in importer id matches the current importer on the repo
        importer_manager = managers_factory.repo_importer_manager()
        importer = importer_manager.get_importer(repo_id)
        if importer_id != importer['id']:
            raise exceptions.MissingResource(importer=importer_id)


class RepoPublishScheduleManager(object):
    @classmethod
    def list(cls, repo_id, distributor_id):
        cls.validate_distributor(repo_id, distributor_id)

        return utils.get_by_resource(RepoDistributor.build_resource_tag(repo_id, distributor_id))

    @classmethod
    def create(cls, repo_id, distributor_id, publish_options, schedule_data):
        """
        Create a new scheduled publish for the given repository and distributor.

        :param repo_id:
        :param distributor_id:
        :param publish_options:
        :param schedule_data:
        :return:
        """
        # validate the input
        cls.validate_distributor(repo_id, distributor_id)
        utils.validate_keys(publish_options, _PUBLISH_OPTION_KEYS)

        utils.validate_initial_schedule_options(schedule_data)

        task = publish.name
        args = [repo_id, distributor_id]
        kwargs = {'overrides': publish_options['override_config']}
        resource = RepoDistributor.build_resource_tag(repo_id, distributor_id)
        schedule = ScheduledCall(schedule_data['schedule'], task, args=args,
                                 kwargs=kwargs, resource=resource)
        schedule.save()

        return schedule

    @classmethod
    def update(cls, repo_id, distributor_id, schedule_id, updates):
        """
        Update an existing scheduled publish for the given repository and distributor.

        :param repo_id:
        :param distributor_id:
        :param schedule_id:
        :param publish_options:
        :param schedule_data:
        :return:
        """

        cls.validate_distributor(repo_id, distributor_id)
        if 'override_config' in updates:
            updates['kwargs'] = {'overrides': updates.pop('override_config')}

        utils.validate_updated_schedule_options(updates)

        utils.update(schedule_id, updates)

    @classmethod
    def delete(cls, repo_id, distributor_id, schedule_id):
        """
        Delete an existing scheduled publish from the given repository and distributor.

        :param repo_id:
        :param distributor_id:
        :param schedule_id:
        :return:
        """
        # validate the input
        cls.validate_distributor(repo_id, distributor_id)

        # remove from the scheduler
        utils.delete(schedule_id)

    @staticmethod
    def validate_distributor(repo_id, distributor_id):
        distributor_manager = managers_factory.repo_distributor_manager()
        distributor_manager.get_distributor(repo_id, distributor_id)
