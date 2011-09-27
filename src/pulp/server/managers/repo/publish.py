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
from gettext import gettext as _
import logging
import sys
import traceback

from pulp.common import dateutils
import pulp.server.content.loader as plugin_loader
from pulp.server.content.conduits.repo_publish import RepoPublishConduit
from pulp.server.db.model.gc_repository import Repo, RepoDistributor
import pulp.server.managers.factory as manager_factory

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- exceptions ---------------------------------------------------------------

class RepoPublishException(Exception):
    """
    Raised when an error occurred during a repo publish. Subclass exceptions are
    used to further categorize the error encountered. The ID of the repository
    that caused the error is included in the exception.
    """
    def __init__(self, repo_id):
        Exception.__init__(self)
        self.repo_id = repo_id

    def __str__(self):
        return _('Exception [%(e)s] raised for repository [%(r)s]') % \
               {'e' : self.__class__.__name__, 'r' : self.repo_id}

class NoDistributor(RepoPublishException):
    """
    Indicates a sync was requested on a repository that is not configured
    with an distributor.
    """
    pass

class MissingRepo(RepoPublishException):
    """
    Indicates an operation was requested against a repo that doesn't exist.
    """
    pass

class MissingDistributorPlugin(RepoPublishException):
    """
    Indicates a repo is configured with an distributor type that could not be
    found in the plugin manager.
    """
    pass

class PublishInProgress(RepoPublishException):
    """
    Indicates a publish was requested for a repo and distributor already in
    the process of publishing the repo.
    """
    pass

class AutoPublishException(Exception):
    """
    Raised when the automatic publishing of a repository results in an error
    for at least one of the distributors. This exception will
    """
    def __init__(self, repo_id, dist_traceback_tuples):
        Exception.__init__(self)
        self.repo_id = repo_id
        self.dist_traceback_tuples = dist_traceback_tuples

    def __str__(self):
        dist_ids = [d[0] for d in self.dist_traceback_tuples]
        return _('Exception [%(e)s] raised for repository [%(r)s] on distributors [%(d)s]' % \
               {'e' : self.__class__.__name__, 'r' : self.repo_id, 'd' : ', '.join(dist_ids)})

# -- manager ------------------------------------------------------------------

class RepoPublishManager:

    def publish(self, repo_id, distributor_id, publish_config_override=None):
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
        @type  publish_config_override: dict
        """

        repo_coll = Repo.get_collection()
        distributor_coll = RepoDistributor.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingRepo(repo_id)

        repo_distributor = distributor_coll.find_one({'repo_id' : repo_id, 'id' : distributor_id})
        if repo_distributor is None:
            raise NoDistributor(repo_id)

        if repo_distributor['publish_in_progress']:
            raise PublishInProgress(repo_id)

        try:
            distributor_instance, distributor_config = \
                plugin_loader.get_distributor_by_id(repo_distributor['distributor_type_id'])
        except plugin_loader.PluginNotFound:
            raise MissingDistributorPlugin(repo_id), None, sys.exc_info()[2]

        # Assemble the data needed for the publish
        repo_manager = manager_factory.repo_manager()
        association_manager = manager_factory.repo_unit_association_manager()
        content_query_manager = manager_factory.content_query_manager()
        conduit = RepoPublishConduit(repo_id, distributor_id, repo_manager, self,
                                     association_manager, content_query_manager)

        # Take the repo's default publish config and merge in the override values
        # for this run alone (don't store it back to the DB)
        publish_config = None
        if repo_distributor['config'] is not None:
            publish_config = dict(repo_distributor['config'])
            if publish_config_override is not None:
                publish_config.update(publish_config_override)

        # Perform the publish
        try:
            repo_distributor['publish_in_progress'] = True
            distributor_coll.save(repo_distributor, safe=True)
            distributor_instance.publish_repo(repo, conduit, distributor_config, publish_config)
        except Exception:
            # Reload the distributor in case the scratchpad is set by the plugin
            repo_distributor = distributor_coll.find_one({'repo_id' : repo_id, 'id' : distributor_id})
            repo_distributor['publish_in_progress'] = False
            repo_distributor['last_publish'] = _publish_finished_timestamp()
            distributor_coll.save(repo_distributor, safe=True)

            _LOG.exception(_('Exception caught from plugin during publish for repo [%(r)s]' % {'r' : repo_id}))
            raise RepoPublishException(repo_id), None, sys.exc_info()[2]

        # Reload the distributor in case the scratchpad is set by the plugin
        repo_distributor = distributor_coll.find_one({'repo_id' : repo_id, 'id' : distributor_id})
        repo_distributor['publish_in_progress'] = False
        repo_distributor['last_publish'] = _publish_finished_timestamp()
        distributor_coll.save(repo_distributor, safe=True)

    def unpublish(self, repo_id, distributor_id):
        pass

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

        @raises AutoPublishException: if one or more of the distributors errors
                during publishing; the exception will contain information on all
                failures
        """

        # Retrieve all auto publish distributors for the repo
        auto_distributors = _auto_distributors(repo_id)

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
                _LOG.exception('Exception on auto distribute call for repo [%s] distributor [%s]' % (repo_id, dist_id))
                error_string = traceback.format_exc()
                error_runs.append( (dist_id, error_string) )

        if len(error_runs) > 0:
            raise AutoPublishException(repo_id, error_runs)

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

        @raises NoDistributor: if there is no distributor identified by the
                given repo ID and distributor ID
        """

        # Validation
        coll = RepoDistributor.get_collection()
        repo_distributor = coll.find_one({'repo_id' : repo_id, 'id' : distributor_id})

        if repo_distributor is None:
            raise NoDistributor(repo_id)

        # Convert to datetime instance
        date_str = repo_distributor['last_publish']

        if date_str is None:
            return date_str
        else:
            instance = dateutils.parse_iso8601_datetime(date_str)
            return instance

# -- utilities ----------------------------------------------------------------

def _publish_finished_timestamp():
    """
    @return: timestamp suitable for indicating when a publish completed
    @rtype:  str
    """
    now = datetime.datetime.now(dateutils.local_tz())
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format

def _auto_distributors(repo_id):
    """
    Returns all distributors for the given repo that are configured for automatic
    publishing.
    """
    dist_coll = RepoDistributor.get_collection()
    auto_distributors = list(dist_coll.find({'repo_id' : repo_id, 'auto_distribute' : True}))
    return auto_distributors