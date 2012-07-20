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
Contains the definitions for all classes related to the distributor's API for
interacting with the Pulp server during a repo publish.
"""

import logging
import sys

from pulp.plugins.conduits.mixins import (DistributorConduitException, RepoScratchPadMixin,
    DistributorScratchPadMixin, RepoGroupDistributorScratchPadMixin, StatusMixin,
    SingleRepoUnitsMixin, MultipleRepoUnitsMixin, PublishReportMixin)
import pulp.server.managers.factory as manager_factory

# -- constants ---------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- classes -----------------------------------------------------------------

class RepoPublishConduit(RepoScratchPadMixin, DistributorScratchPadMixin, StatusMixin,
                         SingleRepoUnitsMixin, PublishReportMixin):
    """
    Used to communicate back into the Pulp server while a distributor is
    publishing a repo. Instances of this call should *not* be cached between
    repo publish runs. Each publish call will be issued its own conduit
    instance that is scoped to that run alone.

    Instances of this class are thread-safe. The distributor implementation is
    allowed to do whatever threading makes sense to optimize the publishing.
    Calls into this instance do not have to be coordinated for thread safety,
    the instance will take care of it itself.
    """

    def __init__(self, repo_id, distributor_id, base_progress_report=None):
        """
        @param repo_id: identifies the repo being published
        @type  repo_id: str

        @param distributor_id: identifies the distributor being published
        @type  distributor_id: str
        """
        RepoScratchPadMixin.__init__(self, repo_id, DistributorConduitException)
        DistributorScratchPadMixin.__init__(self, repo_id, distributor_id)
        StatusMixin.__init__(self, distributor_id, DistributorConduitException, progress_report=base_progress_report)
        SingleRepoUnitsMixin.__init__(self, repo_id, DistributorConduitException)
        PublishReportMixin.__init__(self)

        self.repo_id = repo_id
        self.distributor_id = distributor_id

    def __str__(self):
        return 'RepoPublishConduit for repository [%s]' % self.repo_id

    # -- public ---------------------------------------------------------------

    def last_publish(self):
        """
        Returns the timestamp of the last time this repo was published,
        regardless of the success or failure of the publish. If
        the repo was never published, this call returns None.

        @return: timestamp instance describing the last publish
        @rtype:  datetime or None
        """
        try:
            repo_publish_manager = manager_factory.repo_publish_manager()
            last = repo_publish_manager.last_publish(self.repo_id, self.distributor_id)
            return last
        except Exception, e:
            _LOG.exception('Error getting last publish time for repo [%s]' % self.repo_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]

class RepoGroupPublishConduit(RepoGroupDistributorScratchPadMixin, StatusMixin, MultipleRepoUnitsMixin, PublishReportMixin):

    def __init__(self, group_id, distributor_id):
        RepoGroupDistributorScratchPadMixin.__init__(self, group_id, distributor_id)
        StatusMixin.__init__(self, distributor_id, DistributorConduitException)
        MultipleRepoUnitsMixin.__init__(self, DistributorConduitException)
        PublishReportMixin.__init__(self)

        self.group_id = group_id
        self.distributor_id = distributor_id

    def __str__(self):
        return 'RepoGroupPublishConduit for group [%s]' % self.group_id

    def last_publish(self):
        """
        Returns the timestamp of the last time this repository group was
        publishe, regardless of the success or failure of the publish. If
        the group was never published, this call returns None.

        @return: timestamp describing the last publish
        @rtype:  datetime
        """
        try:
            manager = manager_factory.repo_group_publish_manager()
            last = manager.last_publish(self.group_id, self.distributor_id)
            return last
        except Exception, e:
            _LOG.exception('Error getting last publish time for group [%s]' % self.group_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]