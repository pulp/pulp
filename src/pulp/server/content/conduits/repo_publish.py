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

import pulp.server.content.conduits._common as common_utils
import pulp.server.content.types.database as types_db
from pulp.server.content.plugins.model import PublishReport

# -- constants ---------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- exceptions --------------------------------------------------------------

class RepoPublishConduitException(Exception):
    """
    General exception that wraps any server exception coming out of a conduit
    call.
    """
    pass

# -- classes -----------------------------------------------------------------

class RepoPublishConduit:
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

    def __init__(self,
                 repo_id,
                 distributor_id,
                 repo_manager,
                 repo_distributor_manager,
                 repo_publish_manager,
                 repo_association_manager,
                 repo_association_query_manager,
                 content_query_manager,
                 progress_callback=None):
        """
        @param repo_id: identifies the repo being published
        @type  repo_id: str

        @param distributor_id: identifies the distributor being published
        @type  distributor_id: str

        @param repo_manager: repo CUD manager used by the conduit
        @type  repo_manager: L{RepoManager}

        @param repo_distributor_manager: distributor manager
        @type  repo_distributor_manager: L{RepoDistributorManager}

        @param repo_publish_manager: repo publish manager used by this conduit
        @type  repo_publish_manager: L{RepoPublishManager}

        @param content_query_manager: content query manager used by this conduit
        @type  content_query_manager: L{ContentQueryManager}

        @param progress_callback: used to update the server's knowledge of the
                                  publish progress
        @type  progress_callback: ?
        """
        self.repo_id = repo_id
        self.distributor_id = distributor_id

        self.__repo_manager = repo_manager
        self.__repo_publish_manager = repo_publish_manager
        self.__repo_distributor_manager = repo_distributor_manager
        self.__association_manager = repo_association_manager
        self.__association_query_manager = repo_association_query_manager
        self.__content_query_manager = content_query_manager
        self.__progress_callback = progress_callback

    def __str__(self):
        return _('RepoPublishConduit for repository [%(r)s]' % {'r' : self.repo_id})

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
            last = self.__repo_publish_manager.last_publish(self.repo_id, self.distributor_id)
            return last
        except Exception, e:
            _LOG.exception('Error getting last publish time for repo [%s]' % self.repo_id)
            raise RepoPublishConduitException(e), None, sys.exc_info()[2]

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
            units = self.__association_query_manager.get_units_across_types(self.repo_id, criteria=criteria)

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
            raise RepoPublishConduitException(e), None, sys.exc_info()[2]

    def get_scratchpad(self):
        """
        Returns the value set in the scratchpad for this repository. If no
        value has been set, None is returned.
        """
        try:
            return self.__repo_distributor_manager.get_distributor_scratchpad(self.repo_id, self.distributor_id)
        except Exception, e:
            _LOG.exception('Error getting scratchpad for repository [%s]' % self.repo_id)
            raise RepoPublishConduitException(e), None, sys.exc_info()[2]

    def set_scratchpad(self, value):
        """
        Saves the given value to the scratchpad for this repository. It can later
        be retrieved in subsequent syncs through get_scratchpad. The type for
        the given value is anything that can be stored in the database (string,
        list, dict, etc.).
        """
        try:
            self.__repo_distributor_manager.set_distributor_scratchpad(self.repo_id, self.distributor_id, value)
        except Exception, e:
            _LOG.exception('Error setting scratchpad for repository [%s]' % self.repo_id)
            raise RepoPublishConduitException(e), None, sys.exc_info()[2]

    def build_report(self, summary, details):
        """
        Creates the PublishReport instance that needs to be returned to the Pulp
        server at the end of the publish_repo call.

        @param summary: short log of the publish; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the publish; may be None
        @type  details: any serializable
        """
        r = PublishReport(summary, details)
        return r
