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

import copy
import datetime
from gettext import gettext as _
import logging
import sys

from pulp.common import dateutils
import pulp.server.content.manager as plugin_manager
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
                plugin_manager.get_distributor_by_name(repo_distributor['distributor_type_id'])
        except plugin_manager.PluginNotFound:
            raise MissingDistributorPlugin(repo_id), None, sys.exc_info()[2]

        # Assemble the data needed for the publish
        conduit = RepoPublishConduit(repo_id)

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
            repo_distributor['publish_in_progress'] = False
            repo_distributor['last_publish'] = _publish_finished_timestamp()
            distributor_coll.save(repo_distributor, safe=True)

            _LOG.exception(_('Exception caught from plugin during publish for repo [%(r)s]' % {'r' : repo_id}))
            raise RepoPublishException(repo_id), None, sys.exc_info()[2]

        repo_distributor['publish_in_progress'] = False
        repo_distributor['last_publish'] = _publish_finished_timestamp()
        distributor_coll.save(repo_distributor, safe=True)

    def unpublish(self, repo_id, distributor_id):
        pass

def _publish_finished_timestamp():
    """
    @return: timestamp suitable for indicating when a publish completed
    @rtype:  str
    """
    now = datetime.datetime.now(dateutils.local_tz())
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format