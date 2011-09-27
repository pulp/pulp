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
from gettext import gettext as _

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
                 repo_publish_manager,
                 repo_association_manager,
                 content_query_manager,
                 progress_callback=None):
        """
        @param repo_id: identifies the repo being published
        @type  repo_id: str

        @param distributor_id: identifies the distributor being published
        @type  distributor_id: str

        @param repo_manager: repo CUD manager used by the conduit
        @type  repo_manager: L{RepoManager}

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
        self.__association_manager = repo_association_manager
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
        last = self.__repo_publish_manager.last_publish(self.repo_id, self.distributor_id)
        return last

    def get_content_units(self, unit_type_id=None, filters=None, fields=None):
        """
        Return the content units associated with thre repo to be publised.

        @param unit_type_id: type of units to be returned, None means all types
        @type  unit_type_id: None or str

        @param filters: mongo spec document used to filter the results
        @type  filters: None or dict

        @param fields: list of fields in the returned content units
        @type  fields: None or list (str, ...)

        @return: list of the content units associated with the repo
        @rtype:  list (dict, ...)
        """
        # FIXME: the filters is a little bit of a hack as we shouldn't expose
        # mongo db semantics to the plugin developer
        content_units = []
        associated = self.__association_manager.get_unit_ids(self.repo_id, unit_type_id)
        for unit_type, unit_ids in associated.items():
            spec = filters or {}
            spec.update({'_id': {'$in': unit_ids}})
            units = self.__content_query_manager.list_content_units(unit_type, spec, fields)
            content_units.extend(units)
        return content_units

    def get_scratchpad(self):
        """
        Returns the value set in the scratchpad for this repository. If no
        value has been set, None is returned.
        """
        return self.__repo_manager.get_distributor_scratchpad(self.repo_id, self.distributor_id)

    def set_scratchpad(self, value):
        """
        Saves the given value to the scratchpad for this repository. It can later
        be retrieved in subsequent syncs through get_scratchpad. The type for
        the given value is anything that can be stored in the database (string,
        list, dict, etc.).
        """
        self.__repo_manager.set_distributor_scratchpad(self.repo_id, self.distributor_id, value)
