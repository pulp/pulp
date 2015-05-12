"""
Contains the definitions for all classes related to the distributor's API for
interacting with the Pulp server during a repo publish.
"""

import logging
import sys

from pulp.server import exceptions as pulp_exceptions
from pulp.plugins.conduits.mixins import (
    DistributorConduitException, RepoScratchPadMixin, RepoScratchpadReadMixin,
    DistributorScratchPadMixin, RepoGroupDistributorScratchPadMixin, StatusMixin,
    SingleRepoUnitsMixin, MultipleRepoUnitsMixin, PublishReportMixin)
from pulp.server.db.model.repository import RepoDistributor
from pulp.server.managers import factory as manager_factory


_logger = logging.getLogger(__name__)


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

    def __init__(self, repo_id, distributor_id):
        """
        @param repo_id: identifies the repo being published
        @type  repo_id: str

        @param distributor_id: identifies the distributor being published
        @type  distributor_id: str
        """
        RepoScratchPadMixin.__init__(self, repo_id, DistributorConduitException)
        DistributorScratchPadMixin.__init__(self, repo_id, distributor_id)
        StatusMixin.__init__(self, distributor_id, DistributorConduitException)
        SingleRepoUnitsMixin.__init__(self, repo_id, DistributorConduitException)
        PublishReportMixin.__init__(self)

        self.repo_id = repo_id
        self.distributor_id = distributor_id

    def __str__(self):
        return 'RepoPublishConduit for repository [%s]' % self.repo_id

    def last_publish(self):
        """
        Returns the timestamp of the last time this repo was published, regardless of the success
        or failure of the publish. If the repo was never published, this call returns None.

        :return: timestamp instance describing the last publish
        :rtype:  datetime.datetime or None

        :raises DistributorConduitException: if any errors occur
        """
        try:
            collection = RepoDistributor.get_collection()
            distributor = collection.find_one({'repo_id': self.repo_id, 'id': self.distributor_id})
            if distributor is None:
                raise pulp_exceptions.MissingResource(self.repo_id)
            return distributor['last_publish']
        except Exception, e:
            _logger.exception('Error getting last publish time for repo [%s]' % self.repo_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]


class RepoGroupPublishConduit(RepoGroupDistributorScratchPadMixin, StatusMixin,
                              MultipleRepoUnitsMixin, PublishReportMixin,
                              RepoScratchpadReadMixin):

    def __init__(self, group_id, distributor):
        distributor_id = distributor.get('id')
        RepoGroupDistributorScratchPadMixin.__init__(self, group_id, distributor_id)
        StatusMixin.__init__(self, distributor.get('distributor_type_id'),
                             DistributorConduitException)
        MultipleRepoUnitsMixin.__init__(self, DistributorConduitException)
        PublishReportMixin.__init__(self)
        RepoScratchpadReadMixin.__init__(self, DistributorConduitException)

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
            _logger.exception('Error getting last publish time for group [%s]' % self.group_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]
