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

import pulp.server.managers.factory as manager_factory
import pulp.plugins.conduits._common as conduit_utils
import pulp.plugins.types.database as typedb

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- importer -----------------------------------------------------------------

class ImporterConduitException(Exception):
    """
    General exception that wraps any exception coming out of the Pulp server.
    """
    pass

class BaseImporterConduit:

    def __init__(self, repo_id, importer_id):
        self.repo_id = repo_id
        self.importer_id = importer_id

    def get_scratchpad(self):
        """
        Returns the value set for the importer's private scratchpad for this
        repository. If no value has been set, None is returned.

        @return: value saved for the repository and this importer
        @rtype:  <serializable>

        @raise ImporterConduitException: wraps any exception that may occur
               in the Pulp server
        """

        try:
            importer_manager = manager_factory.repo_importer_manager()
            value = importer_manager.get_importer_scratchpad(self.repo_id)
            return value
        except Exception, e:
            _LOG.exception(_('Error getting scratchpad for repo [%(r)s]') % {'r' : self.repo_id})
            raise ImporterConduitException(e), None, sys.exc_info()[2]

    def set_scratchpad(self, value):
        """
        Saves the given value to the importer's private scratchpad for this
        repository. It can later be retrieved in subsequent importer operations
        through get_scratchpad. The type for the given value is anything that
        can be stored in the database (string, list, dict, etc.).

        @param value: will overwrite the existing scratchpad
        @type  value: <serializable>

        @raise ImporterConduitException: wraps any exception that may occur
               in the Pulp server
        """
        try:
            importer_manager = manager_factory.repo_importer_manager()
            importer_manager.set_importer_scratchpad(self.repo_id, value)
        except Exception, e:
            _LOG.exception(_('Error setting scratchpad for repo [%(r)s]') % {'r' : self.repo_id})
            raise ImporterConduitException(e), None, sys.exc_info()[2]

    def get_repo_scratchpad(self):
        """
        Returns the repository-level scratchpad for this repository. The
        repository-level scratchpad can be seen and edited by all importers
        and distributors on the repository. Care should be taken to not destroy
        any data set by another plugin. This may be used to communicate between
        importers and distributors relevant data for the repository.

        @raise ImporterConduitException: wraps any exception that may occur
               in the Pulp server
        """
        try:
            repo_manager = manager_factory.repo_manager()
            value = repo_manager.get_repo_scratchpad(self.repo_id)
            return value
        except Exception, e:
            _LOG.exception(_('Error getting repository scratchpad for repo [%(r)s]') % {'r' : self.repo_id})
            raise ImporterConduitException(e), None, sys.exc_info()[2]

    def set_repo_scratchpad(self, value):
        """
        Saves the given value to the repository-level scratchpad for this
        repository. It can be retrieved in subsequent importer operations
        through get_repo_scratchpad. The type for the given value is anything
        that can be stored in the database (string, list, dict, etc.).

        @param value: will overwrite the existing scratchpad
        @type  value: <serializable>

        @raise ImporterConduitException: wraps any exception that may occur
               in the Pulp server
        """
        try:
            repo_manager = manager_factory.repo_manager()
            repo_manager.set_repo_scratchpad(self.repo_id, value)
        except Exception, e:
            _LOG.exception(_('Error setting repository scratchpad for repo [%(r)s]') % {'r' : self.repo_id})
            raise ImporterConduitException(e), None, sys.exc_info()[2]

# -- distributor --------------------------------------------------------------

class DistributorConduitException(Exception):
    """
    General exception that wraps any exception coming out of the Pulp server.
    """
    pass

class BaseDistributorConduit:

    def __init__(self, repo_id, distributor_id):
        self.repo_id = repo_id
        self.distributor_id = distributor_id

    def get_scratchpad(self):
        """
        Returns the value set in the scratchpad for this repository. If no
        value has been set, None is returned.

        @return: value saved for the repository and this distributor
        @rtype:  <serializable>

        @raises DistributorConduitException: wraps any exception that may occur
                in the Pulp server
        """
        try:
            distributor_manager = manager_factory.repo_distributor_manager()
            value = distributor_manager.get_distributor_scratchpad(self.repo_id, self.distributor_id)
            return value
        except Exception, e:
            _LOG.exception('Error getting scratchpad for repository [%s]' % self.repo_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]

    def set_scratchpad(self, value):
        """
        Saves the given value to the scratchpad for this repository. It can later
        be retrieved in subsequent syncs through get_scratchpad. The type for
        the given value is anything that can be stored in the database (string,
        list, dict, etc.).

        @param value: will overwrite the existing scratchpad
        @type  value: <serializable>

        @raises DistributorConduitException: wraps any exception that may occur
                in the Pulp server
        """
        try:
            distributor_manager = manager_factory.repo_distributor_manager()
            distributor_manager.set_distributor_scratchpad(self.repo_id, self.distributor_id, value)
        except Exception, e:
            _LOG.exception('Error setting scratchpad for repository [%s]' % self.repo_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]

    def get_repo_scratchpad(self):
        """
        Returns the repository-level scratchpad for this repository. The
        repository-level scratchpad can be seen and edited by all importers
        and distributors on the repository. Care should be taken to not destroy
        any data set by another plugin. This may be used to communicate between
        importers and distributors relevant data for the repository.

        @raise ImporterConduitException: wraps any exception that may occur
               in the Pulp server
        """
        try:
            repo_manager = manager_factory.repo_manager()
            value = repo_manager.get_repo_scratchpad(self.repo_id)
            return value
        except Exception, e:
            _LOG.exception(_('Error getting repository scratchpad for repo [%(r)s]') % {'r' : self.repo_id})
            raise ImporterConduitException(e), None, sys.exc_info()[2]

    def set_repo_scratchpad(self, value):
        """
        Saves the given value to the repository-level scratchpad for this
        repository. It can be retrieved in subsequent distributor operations
        through get_repo_scratchpad. The type for the given value is anything
        that can be stored in the database (string, list, dict, etc.).

        @param value: will overwrite the existing scratchpad
        @type  value: <serializable>

        @raise ImporterConduitException: wraps any exception that may occur
               in the Pulp server
        """
        try:
            repo_manager = manager_factory.repo_manager()
            repo_manager.set_repo_scratchpad(self.repo_id, value)
        except Exception, e:
            _LOG.exception(_('Error setting repository scratchpad for repo [%(r)s]') % {'r' : self.repo_id})
            raise ImporterConduitException(e), None, sys.exc_info()[2]


# -- profiler -----------------------------------------------------------------

class ProfilerConduitException(Exception):
    """
    General exception that wraps any exception coming out of the Pulp server.
    """
    pass

class ProfilerBaseConduit:
    pass

class ProfilerConduit(ProfilerBaseConduit):

    def get_profile(self, consumer_id, content_type):
        """
        Get a unit profile by consumer ID.

        @param consumer_id: A consumer ID.
        @type consumer_id: str

        @param content_type: A profile (content) type ID.
        @type content_type: str

        @return: The requested profile.
        @rtype: dict

        @raise ProfilerConduitException: On error.
        """
        try:
            manager = manager_factory.consumer_profile_manager()
            return manager.get_profile(consumer_id, content_type)
        except Exception, e:
            _LOG.exception(_('Error fetching profile for consumer [%(c)s]') % {'c' : consumer_id})
            raise ProfilerConduitException(e), None, sys.exc_info()[2]

    def get_bindings(self, consumer_id):
        """
        Get a list of bound repository IDs.

        @param consumer_id: A consumer ID.
        @type consumer_id: str

        @return: A list of bound repository IDs.
        @rtype: list
        """
        manager = manager_factory.consumer_bind_manager()
        bindings = manager.find_by_consumer(consumer_id)
        return [b['repo_id'] for b in bindings]

    def get_units(self, repo_id, criteria=None):
        """
        Returns the collection of content units associated with the
        specified repository IDs.

        @param repo_id: A repo ID.
        @type repo_id: list

        @param criteria: used to scope the returned results or the data within
        @type  criteria: L{Criteria}

        @return: list of unit instances
        @rtype:  list of L{AssociatedUnit}
        """
        try:
            result = []
            manager = manager_factory.repo_unit_association_query_manager()
            units = manager.get_units_across_types(repo_id, criteria=criteria)
            typedefs = dict([(u['unit_type_id'],{}) for u in units])
            for type_id in typedefs.keys():
                typedefs[type_id] = typedb.type_definition(type_id)
            for unit in units:
                type_id = unit['unit_type_id']
                u = conduit_utils.to_plugin_unit(unit, typedefs[type_id])
                result.append(u)
            return result
        except Exception, e:
            _LOG.exception('Error getting units for repository [%s]' % repo_id)
            raise ProfilerConduitException(e), None, sys.exc_info()[2]