# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
Contains the manager class and exceptions for performing repository publish
operations. All classes and functions in this module run synchronously; any
need to execute syncs asynchronously must be handled at a higher layer.
"""

import datetime
import isodate
import logging
import sys
import traceback
from gettext import gettext as _

from celery import task

from pulp.common import dateutils, constants
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.model import PublishReport
from pulp.plugins.conduits.repo_publish import RepoPublishConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.server.db.model.repository import Repo, RepoDistributor, RepoPublishResult
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.exceptions import MissingResource, PulpExecutionException, InvalidValue
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.repo import _common as common_utils
from pulp.server.async.tasks import Task


logger = logging.getLogger(__name__)


class RepoPublishManager(object):

    @staticmethod
    def publish(repo_id, distributor_id, publish_config_override=None):
        """
        Requests the given distributor publish the repository it is configured
        on.

        The publish operation is executed synchronously in the caller's thread
        and will block until it is completed. The caller must take the necessary
        steps to address the fact that a publish call may be time intensive.

        @param repo_id: identifies the repo being published
        @type  repo_id: str

        @param distributor_id: identifies the repo's distributor to publish
        @type  distributor_id: str

        @param publish_config_override: optional config values to use for this
                                        publish call only
        @type  publish_config_override: dict, None
        """

        repo_coll = Repo.get_collection()
        distributor_coll = RepoDistributor.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        repo_distributor = distributor_coll.find_one({'repo_id' : repo_id, 'id' : distributor_id})
        if repo_distributor is None:
            raise MissingResource(repository=repo_id, distributor=distributor_id)

        distributor_instance, distributor_config = RepoPublishManager.\
            _get_distributor_instance_and_config(repo_id, distributor_id)

        if distributor_instance is None:
            raise MissingResource(repo_id), None, sys.exc_info()[2]

        dispatch_context = dispatch_factory.context()
        dispatch_context.set_cancel_control_hook(distributor_instance.cancel_publish_repo)

        # Assemble the data needed for the publish
        conduit = RepoPublishConduit(repo_id, distributor_id)

        call_config = PluginCallConfiguration(distributor_config, repo_distributor['config'],
                                              publish_config_override)
        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.distributor_working_dir(
            repo_distributor['distributor_type_id'], repo_id, mkdir=True)

        # Fire events describing the publish state
        fire_manager = manager_factory.event_fire_manager()
        fire_manager.fire_repo_publish_started(repo_id, distributor_id)
        result = RepoPublishManager._do_publish(repo, distributor_id, distributor_instance,
                                                transfer_repo, conduit, call_config)
        fire_manager.fire_repo_publish_finished(result)

        dispatch_context.clear_cancel_control_hook()

    @staticmethod
    def _get_distributor_instance_and_config(repo_id, distributor_id):
        repo_distributor_manager = manager_factory.repo_distributor_manager()
        try:
            repo_distributor = repo_distributor_manager.get_distributor(repo_id, distributor_id)
            distributor, config = plugin_api.get_distributor_by_id(
                repo_distributor['distributor_type_id'])
        except (MissingResource, plugin_exceptions.PluginNotFound):
            distributor = None
            config = None
        return distributor, config

    @staticmethod
    def _do_publish(repo, distributor_id, distributor_instance, transfer_repo, conduit,
                    call_config):

        distributor_coll = RepoDistributor.get_collection()
        publish_result_coll = RepoPublishResult.get_collection()
        repo_id = repo['id']

        # Perform the publish
        publish_start_timestamp = _now_timestamp()
        try:
            publish_report = distributor_instance.publish_repo(transfer_repo, conduit, call_config)
        except Exception, e:
            publish_end_timestamp = _now_timestamp()

            # Reload the distributor in case the scratchpad is set by the plugin
            repo_distributor = distributor_coll.find_one(
                {'repo_id' : repo_id, 'id' : distributor_id})
            repo_distributor['last_publish'] = publish_end_timestamp
            distributor_coll.save(repo_distributor, safe=True)

            # Add a publish history entry for the run
            result = RepoPublishResult.error_result(
                repo_id, repo_distributor['id'], repo_distributor['distributor_type_id'],
                publish_start_timestamp, publish_end_timestamp, e, sys.exc_info()[2])
            publish_result_coll.save(result, safe=True)

            logger.exception(
                _('Exception caught from plugin during publish for repo [%(r)s]' % {'r' : repo_id}))
            raise PulpExecutionException(), None, sys.exc_info()[2]

        publish_end_timestamp = _now_timestamp()

        # Reload the distributor in case the scratchpad is set by the plugin
        repo_distributor = distributor_coll.find_one({'repo_id' : repo_id, 'id' : distributor_id})
        repo_distributor['last_publish'] = _now_timestamp()
        distributor_coll.save(repo_distributor, safe=True)

        # Add a publish entry
        if publish_report is not None and isinstance(publish_report, PublishReport):
            summary = publish_report.summary
            details = publish_report.details
            if publish_report.success_flag:
                logger.debug('publish succeeded for repo [%s] with distributor ID [%s]' % (
                           repo_id, distributor_id))
                result_code = RepoPublishResult.RESULT_SUCCESS
            else:
                logger.info('publish failed for repo [%s] with distributor ID [%s]' % (
                           repo_id, distributor_id))
                logger.debug('summary for repo [%s] with distributor ID [%s]: %s' % (
                           repo_id, distributor_id, summary))
                result_code = RepoPublishResult.RESULT_FAILED
        else:
            msg = _('Plugin type [%(type)s] on repo [%(repo)s] did not return a valid publish '
                    'report')
            msg = msg % {'type': repo_distributor['distributor_type_id'], 'repo': repo_id}
            logger.warn(msg)

            summary = details = _('Unknown')
            result_code = RepoPublishResult.RESULT_SUCCESS

        result = RepoPublishResult.expected_result(
            repo_id, repo_distributor['id'], repo_distributor['distributor_type_id'],
            publish_start_timestamp, publish_end_timestamp, summary, details, result_code)
        publish_result_coll.save(result, safe=True)
        return result

    def auto_publish_for_repo(self, repo_id):
        """
        Calls publish on all distributors that are configured to be automatically
        called for the given repo. Each distributor is called serially. The order
        in which they are executed is determined simply by distributor ID (sorted
        ascending alphabetically).

        All automatic distributors will be called, regardless of whether or not
        one raises an error. All failed publish calls will be collaborated into
        a single exception.

        If no distributors are configured for automatic publishing, this call
        does nothing.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @raise OperationFailed: if one or more of the distributors errors
                during publishing; the exception will contain information on all
                failures
        """

        # Retrieve all auto publish distributors for the repo
        auto_distributors = self.auto_distributors(repo_id)

        if len(auto_distributors) is 0:
            return

        # Call publish on each matching distributor, keeping a running track
        # of failed calls
        error_runs = [] # contains tuple of dist_id and error string
        for dist in auto_distributors:
            dist_id = dist['id']
            try:
                self.publish(repo_id, dist_id, None)
            except Exception:
                logger.exception('Exception on auto distribute call for repo [%s] distributor [%s]' % (repo_id, dist_id))
                error_string = traceback.format_exc()
                error_runs.append( (dist_id, error_string) )

        if len(error_runs) > 0:
            raise PulpExecutionException()

    def last_publish(self, repo_id, distributor_id):
        """
        Returns the timestamp of the last publish call, regardless of its
        success or failure. If the repo has never been published, returns None.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param distributor_id: identifies the repo's distributor
        @type  distributor_id: str

        @return: timestamp of the last publish
        @rtype:  datetime or None

        @raise MissingResource: if there is no distributor identified by the
                given repo ID and distributor ID
        """

        # Validation
        coll = RepoDistributor.get_collection()
        repo_distributor = coll.find_one({'repo_id' : repo_id, 'id' : distributor_id})

        if repo_distributor is None:
            raise MissingResource(repo_id)

        # Convert to datetime instance
        date_str = repo_distributor['last_publish']

        if date_str is None:
            return date_str
        else:
            instance = dateutils.parse_iso8601_datetime(date_str)
            return instance

    def publish_history(self, repo_id, distributor_id, limit=None, sort=constants.SORT_DESCENDING,
                        start_date=None, end_date=None):
        """
        Returns publish history entries for the give repo, sorted from most
        recent to oldest. If there are no entries, an empty list is returned.

        :param repo_id:         identifies the repo
        :type  repo_id:         str
        :param distributor_id:  identifies the distributor to retrieve history for
        :type  distributor_id:  str
        :param limit:           if specified, the query will only return up to this amount of entries;
                                default is to return the entire publish history
        :type  limit:           int
        :param sort:            Indicates the sort direction of the results, which are sorted by start date. Options
                                are "ascending" and "descending". Descending is the default.
        :type  sort: str
        :param start_date:      if specified, no events prior to this date will be returned. Expected to be an
                                iso8601 datetime string.
        :type  start_date:      str
        :param end_date:        if specified, no events after this date will be returned. Expected to be an
                                iso8601 datetime string.
        :type  end_date:        str

        :return: list of publish history result instances
        :rtype:  list

        :raise MissingResource: if repo_id does not reference a valid repo
        :raise InvalidValue: if one or more of the options have invalid values
        """

        # Validation
        repo = Repo.get_collection().find_one({'id': repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        dist = RepoDistributor.get_collection().find_one({'repo_id': repo_id, 'id': distributor_id})
        if dist is None:
            raise MissingResource(distributor_id)

        invalid_values = []
        # Verify the limit makes sense
        if limit is not None:
            try:
                limit = int(limit)
                if limit < 1:
                    invalid_values.append('limit')
            except ValueError:
                invalid_values.append('limit')

        # Verify the sort direction is valid
        if sort not in constants.SORT_DIRECTION:
            invalid_values.append('sort')

        # Verify that start_date and end_date is valid
        if start_date is not None:
            try:
                dateutils.parse_iso8601_datetime(start_date)
            except (ValueError, isodate.ISO8601Error):
                invalid_values.append('start_date')
        if end_date is not None:
            try:
                dateutils.parse_iso8601_datetime(end_date)
            except (ValueError, isodate.ISO8601Error):
                invalid_values.append('end_date')
        # Report any invalid values
        if invalid_values:
            raise InvalidValue(invalid_values)

        # Assemble the mongo search parameters
        search_params = {'repo_id': repo_id, 'distributor_id': distributor_id}
        date_range = {}
        if start_date:
            date_range['$gte'] = start_date
        if end_date:
            date_range['$lte'] = end_date
        if len(date_range) > 0:
            search_params['started'] = date_range

        # Retrieve the entries
        cursor = RepoPublishResult.get_collection().find(search_params)
        # Sort the results on the 'started' field. By default, descending order is used
        cursor.sort('started', direction=constants.SORT_DIRECTION[sort])
        if limit is not None:
            cursor.limit(limit)

        return list(cursor)

    def auto_distributors(self, repo_id):
        """
        Returns all distributors for the given repo that are configured for automatic
        publishing.
        """
        dist_coll = RepoDistributor.get_collection()
        auto_distributors = list(dist_coll.find({'repo_id' : repo_id, 'auto_publish' : True}))
        return auto_distributors


publish = task(RepoPublishManager.publish, base=Task, ignore_result=True)


def _now_timestamp():
    """
    @return: timestamp suitable for indicating when a publish completed
    @rtype:  str
    """
    now = datetime.datetime.now(dateutils.local_tz())
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format
