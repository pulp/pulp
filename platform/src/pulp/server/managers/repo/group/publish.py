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

from pulp.common import dateutils
from pulp.plugins import loader as plugin_loader
from pulp.plugins.conduits.repo_publish import RepoGroupPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import PublishReport
from pulp.server.db.model.repo_group import RepoGroupPublishResult, RepoGroupDistributor
from pulp.server.exceptions import MissingResource, PulpExecutionException
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.repo import _common as common_utils

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoGroupPublishManager(object):

    def publish(self, group_id, distributor_id, publish_config_override=None):
        """
        Requests the given distributor publish the repository group.

        @param group_id: identifies the repo group
        @type  group_id: str

        @param distributor_id: identifies the group's distributor
        @type  distributor_id: str

        @param publish_config_override: values to pass the plugin for this
               publish call alone
        @type  publish_config_override: dict
        """

        group_query_manager = manager_factory.repo_group_query_manager()
        distributor_manager = manager_factory.repo_group_distributor_manager()

        # Validation
        group = group_query_manager.get_group(group_id)
        distributor = distributor_manager.get_distributor(group_id, distributor_id)
        distributor_type_id = distributor['distributor_type_id']

        try:
            distributor_instance, plugin_config =\
                plugin_loader.get_group_distributor_by_id(distributor_type_id)
        except plugin_loader.PluginNotFound:
            raise MissingResource(distributor_type=distributor_type_id), None, sys.exc_info()[2]

        # Assemble the data needed for publish
        conduit = RepoGroupPublishConduit(group_id, distributor_id)

        call_config = PluginCallConfiguration(plugin_config, distributor['config'], publish_config_override)
        transfer_group = common_utils.to_transfer_repo_group(group)
        transfer_group.working_dir = common_utils.group_distributor_working_dir(distributor_type_id, group_id)

        # TODO: Add events for group publish start/complete
        self._do_publish(transfer_group, distributor_id, distributor_instance, conduit, call_config)

    def _do_publish(self, group, distributor_id, distributor_instance, conduit, call_config):

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

            _LOG.exception('Exception caught from plugin during publish call for group [%s]' % group_id)
            raise PulpExecutionException(e), None, sys.exc_info()[2]

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
            _LOG.warn('Plugin type [%s] did not return a valid publish report' % distributor['distributor_type_id'])

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
        @rtype:  datetime
        """
        distributor = manager_factory.repo_group_distributor_manager().get_distributor(group_id, distributor_id)

        date = distributor['last_publish']

        if date is not None:
            date = dateutils.parse_iso8601_datetime(date)

        return date

def _now_timestamp():
    """
    @return: timestamp suitable for indicating when a publish completed
    @rtype:  str
    """
    now = datetime.datetime.now(dateutils.local_tz())
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format
