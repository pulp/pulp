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

from gettext import gettext as _
import logging
import sys
import datetime

from celery import task

from pulp.common import dateutils
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.conduits.repo_publish import RepoGroupPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import PublishReport
from pulp.server.async.tasks import Task
from pulp.server.db.model.repo_group import RepoGroupPublishResult, RepoGroupDistributor
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.repo import _common as common_utils


logger = logging.getLogger(__name__)


class RepoGroupPublishManager(object):

    @staticmethod
    def publish(group_id,
                distributor_id,
                publish_config_override=None):
        """
        Requests the given distributor publish the repository group.

        :param group_id:                identifies the repo group
        :type  group_id:                str
        :param distributor_id:          identifies the group's distributor
        :type  distributor_id:          str
        :param publish_config_override: values to pass the plugin for this publish call alone
        :type  publish_config_override: dict
        """
        distributor_manager = manager_factory.repo_group_distributor_manager()
        distributor = distributor_manager.get_distributor(group_id, distributor_id)
        distributor_type_id = distributor['distributor_type_id']
        distributor_instance, plugin_config = plugin_api.get_group_distributor_by_id(distributor_type_id)

        group_query_manager = manager_factory.repo_group_query_manager()

        # Validation
        group = group_query_manager.get_group(group_id)
        distributor_type_id = distributor['distributor_type_id']

        # Assemble the data needed for publish
        conduit = RepoGroupPublishConduit(group_id, distributor)

        call_config = PluginCallConfiguration(plugin_config, distributor['config'],
                                              publish_config_override)
        transfer_group = common_utils.to_transfer_repo_group(group)
        transfer_group.working_dir = common_utils.group_distributor_working_dir(distributor_type_id,
                                                                                group_id)

        # TODO: Add events for group publish start/complete
        RepoGroupPublishManager._do_publish(transfer_group, distributor_id, distributor_instance,
                                            conduit, call_config)

    @staticmethod
    def _do_publish(group, distributor_id, distributor_instance, conduit, call_config):

        distributor_coll = RepoGroupDistributor.get_collection()
        publish_result_coll = RepoGroupPublishResult.get_collection()
        group_id = group.id

        # Perform the publish
        publish_start_timestamp = _now_timestamp()
        try:
            report = distributor_instance.publish_group(group, conduit, call_config)
        except Exception, e:
            publish_end_timestamp = _now_timestamp()

            # Reload the distributor in case the scratchpad is changed by the plugin
            distributor = distributor_coll.find_one({'id' : distributor_id, 'repo_group_id' : group_id})
            distributor['last_publish'] = publish_end_timestamp
            distributor_coll.save(distributor)

            # Add a publish history entry for the run
            result = RepoGroupPublishResult.error_result(group_id, distributor_id,
                     distributor['distributor_type_id'], publish_start_timestamp,
                     publish_end_timestamp, e, sys.exc_info()[2])
            publish_result_coll.save(result, safe=True)

            raise

        publish_end_timestamp = _now_timestamp()

        # Reload the distributor in case the scratchpad is changed by the plugin
        distributor = distributor_coll.find_one({'id' : distributor_id, 'repo_group_id' : group_id})
        distributor['last_publish'] = publish_end_timestamp
        distributor_coll.save(distributor)

        # Add a publish entry
        if report is not None and isinstance(report, PublishReport):
            summary = report.summary
            details = report.details
            if report.success_flag:
                result = RepoGroupPublishResult.expected_result(group_id, distributor_id,
                         distributor['distributor_type_id'], publish_start_timestamp,
                         publish_end_timestamp, summary, details)
            else:
                result = RepoGroupPublishResult.failed_result(group_id, distributor_id,
                         distributor['distributor_type_id'], publish_start_timestamp,
                         publish_end_timestamp, summary, details)
        else:
            msg = _('Plugin type [%(t)s] did not return a valid publish report')
            msg = msg % {'t': distributor['distributor_type_id']}
            logger.warn(msg)

            summary = details = _('Unknown')
            result = RepoGroupPublishResult.expected_result(group_id, distributor_id,
                     distributor['distributor_type_id'], publish_start_timestamp,
                     publish_end_timestamp, summary, details)

        publish_result_coll.save(result, safe=True)
        return result

    def last_publish(self, group_id, distributor_id):
        """
        Returns the timestamp of the last publish call, regardless of its
        success or failure. If the group has never been published, returns
        None.

        @param group_id: identifies the repo group
        @type  group_id: str

        @param distributor_id: identifies the group's distributor
        @type  distributor_id: str

        @return: timestamp of the last publish or None
        @rtype:  datetime.datetime
        """
        distributor = manager_factory.repo_group_distributor_manager().get_distributor(group_id, distributor_id)

        date = distributor['last_publish']

        if date is not None:
            date = dateutils.parse_iso8601_datetime(date)

        return date


publish = task(RepoGroupPublishManager.publish, base=Task, ignore_result=True)


def _now_timestamp():
    """
    @return: UTC timestamp suitable for indicating when a publish completed
    @rtype:  str
    """
    now = dateutils.now_utc_datetime_with_tzinfo()
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format
