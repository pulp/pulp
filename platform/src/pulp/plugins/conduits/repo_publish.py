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

from gettext import gettext as _
import logging
import sys

from pulp.plugins.conduits._base import BaseDistributorConduit, DistributorConduitException
import pulp.plugins.conduits._common as common_utils
import pulp.plugins.types.database as types_db
from pulp.plugins.model import PublishReport
import pulp.server.dispatch.factory as dispatch_factory
import pulp.server.managers.factory as manager_factory

# -- constants ---------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- classes -----------------------------------------------------------------

class RepoPublishConduit(BaseDistributorConduit):
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
        BaseDistributorConduit.__init__(self, repo_id, distributor_id)

        self.repo_id = repo_id
        self.distributor_id = distributor_id

        if base_progress_report is not None:
            self.progress_report = base_progress_report
        else:
            self.progress_report = {}

        self._repo_manager = manager_factory.repo_manager()
        self._repo_publish_manager = manager_factory.repo_publish_manager()
        self._repo_distributor_manager = manager_factory.repo_distributor_manager()
        self._association_manager = manager_factory.repo_unit_association_manager()
        self._association_query_manager = manager_factory.repo_unit_association_query_manager()
        self._content_query_manager = manager_factory.content_manager()

    def __str__(self):
        return _('RepoPublishConduit for repository [%(r)s]' % {'r' : self.repo_id})

    # -- public ---------------------------------------------------------------

    def set_progress(self, status):
        """
        Informs the server of the current state of the publish operation. The
        contents of the status is dependent on how the distributor
        implementation chooses to divide up the publish process.

        @param status: contains arbitrary data to describe the state of the
               publish; the contents may contain whatever information is relevant
               to the distributor implementation so long as it is serializable
        """
        try:
            self.progress_report[self.distributor_id] = status
            context = dispatch_factory.context()
            context.report_progress(self.progress_report)
        except Exception, e:
            _LOG.exception('Exception from server setting progress for repository [%s]' % self.repo_id)
            try:
                _LOG.error('Progress value: %s' % str(status))
            except:
                # Best effort to print this, but if its that grossly unserializable
                # the log will tank and we don't want that exception to bubble up
                pass
            raise DistributorConduitException(e), None, sys.exc_info()[2]

    def last_publish(self):
        """
        Returns the timestamp of the last time this repo was published,
        regardless of the success or failure of the publish. If
        the repo was never published, this call returns None.

        @return: timestamp instance describing the last publish
        @rtype:  datetime or None
        """
        try:
            last = self._repo_publish_manager.last_publish(self.repo_id, self.distributor_id)
            return last
        except Exception, e:
            _LOG.exception('Error getting last publish time for repo [%s]' % self.repo_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]

    def get_units(self, criteria=None):
        """
        Returns the collection of content units associated with the repository
        being published.

        @param criteria: used to scope the returned results or the data within
        @type  criteria: L{Criteria}

        @return: list of unit instances
        @rtype:  list of L{AssociatedUnit}
        """

        try:
            units = self._association_query_manager.get_units_across_types(self.repo_id, criteria=criteria)

            all_units = []

            # Load all type definitions in use so we don't hammer the database
            unique_type_defs = set([u['unit_type_id'] for u in units])
            type_defs = {}
            for def_id in unique_type_defs:
                type_def = types_db.type_definition(def_id)
                type_defs[def_id] = type_def

            # Convert to transfer object
            for unit in units:
                type_id = unit['unit_type_id']
                u = common_utils.to_plugin_unit(unit, type_defs[type_id])
                all_units.append(u)

            return all_units
        except Exception, e:
            _LOG.exception('Error getting units for repository [%s]' % self.repo_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]

    def build_success_report(self, summary, details):
        """
        Creates the PublishReport instance that needs to be returned to the Pulp
        server at the end of the publish_repo call.

        @param summary: short log of the publish; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the publish; may be None
        @type  details: any serializable
        """
        r = PublishReport(True, summary, details)
        return r

    def build_failure_report(self, summary, details):
        """
        Creates the PublishReport instance that needs to be returned to the Pulp
        server at the end of the publish_repo call. The report built in this
        fashion will indicate the publish operation has gracefully failed
        (as compared to an unexpected exception bubbling up).

        @param summary: short log of the publish; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the publish; may be None
        @type  details: any serializable
        """
        r = PublishReport(False, summary, details)
        return r
