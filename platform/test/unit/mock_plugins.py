#!/usr/bin/python
# Copyright (c) 2011 Red Hat, Inc.
#
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
Contains mock importer and distributor implementations.

Unless otherwise specified, each mock will contain a class-level reset()
method that must be called during test cleanup. This will ensure the state
of any captured data as well as any configured behavior reverts back to
the defaults.
"""

import mock

from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.model import SyncReport, PublishReport, ApplicabilityReport

# -- constants ----------------------------------------------------------------

# Used when reverting the monkey patch
_ORIG_GET_DISTRIBUTOR_BY_ID = None
_ORIG_GET_GROUP_DISTRIBUTOR_BY_ID = None
_ORIG_GET_IMPORTER_BY_ID = None
_ORIG_GET_GROUP_IMPORTER_BY_ID = None
_ORIG_GET_PROFILER_BY_TYPE = None

# -- plugin classes -----------------------------------------------------------

class MockImporter(mock.Mock):

    @classmethod
    def metadata(cls):
        return {'types' : ['mock-type']}

class MockGroupImporter(mock.Mock):

    @classmethod
    def metadata(cls):
        return {'types' : ['mock-type']}

class MockDistributor(mock.Mock):

    @classmethod
    def metadata(cls):
        return {'types' : ['mock-type']}

class MockGroupDistributor(mock.Mock):

    @classmethod
    def metadata(cls):
        return {'types' : ['mock-type']}

class MockProfiler(mock.Mock):

    @classmethod
    def metadata(cls):
        return {'types' : ['mock-type', 'type-1', 'errata']}

class MockRpmProfiler(mock.Mock):

    @classmethod
    def metadata(cls):
        return {'types' : ['rpm']}

# -- mock instances -----------------------------------------------------------

MOCK_IMPORTER = MockImporter()
MOCK_GROUP_IMPORTER = MockGroupImporter()
MOCK_DISTRIBUTOR = MockDistributor()
MOCK_DISTRIBUTOR_2 = MockDistributor()
MOCK_GROUP_DISTRIBUTOR = MockGroupDistributor()
MOCK_GROUP_DISTRIBUTOR_2 = MockGroupDistributor()
MOCK_PROFILER = MockProfiler()
MOCK_PROFILER_RPM = MockRpmProfiler()
MOCK_PROFILERS = [MOCK_PROFILER, MOCK_PROFILER_RPM]

# Set by install; can edit these during a test to simulate a plugin being uninstalled
DISTRIBUTOR_MAPPINGS = None
GROUP_DISTRIBUTOR_MAPPINGS = None
IMPORTER_MAPPINGS = None
GROUP_IMPORTER_MAPPINGS = None
PROFILER_MAPPINGS = None

# -- public -------------------------------------------------------------------

def install():
    """
    Called during test setup to monkey patch the plugin loader for testing.
    """

    # -- update plugin loader inventory ---------------------------------------

    plugin_api._create_manager()

    plugin_api._MANAGER.importers.add_plugin('mock-importer', MockImporter, {})
    plugin_api._MANAGER.group_importers.add_plugin('mock-group-importer', MockGroupImporter, {})
    plugin_api._MANAGER.distributors.add_plugin('mock-distributor', MockDistributor, {})
    plugin_api._MANAGER.distributors.add_plugin('mock-distributor-2', MockDistributor, {})
    plugin_api._MANAGER.group_distributors.add_plugin('mock-group-distributor', MockGroupDistributor, {})
    plugin_api._MANAGER.group_distributors.add_plugin('mock-group-distributor-2', MockGroupDistributor, {})
    plugin_api._MANAGER.profilers.add_plugin('mock-profiler', MockProfiler, {})
    plugin_api._MANAGER.profilers.add_plugin('mock-rpm-profiler', MockRpmProfiler, {})

    # -- return mock instances instead of ephemeral ones ----------------------

    # Save the state of the original plugin loader so it can be reverted
    global _ORIG_GET_DISTRIBUTOR_BY_ID
    global _ORIG_GET_GROUP_DISTRIBUTOR_BY_ID
    global _ORIG_GET_IMPORTER_BY_ID
    global _ORIG_GET_GROUP_IMPORTER_BY_ID
    global _ORIG_GET_PROFILER_BY_TYPE

    _ORIG_GET_DISTRIBUTOR_BY_ID = plugin_api.get_distributor_by_id
    _ORIG_GET_GROUP_DISTRIBUTOR_BY_ID = plugin_api.get_group_distributor_by_id
    _ORIG_GET_IMPORTER_BY_ID = plugin_api.get_importer_by_id
    _ORIG_GET_GROUP_IMPORTER_BY_ID = plugin_api.get_group_importer_by_id
    _ORIG_GET_PROFILER_BY_TYPE = plugin_api.get_profiler_by_type

    # Setup the importer/distributor mappings that return the mock instances
    global DISTRIBUTOR_MAPPINGS
    DISTRIBUTOR_MAPPINGS = {
            'mock-distributor' : MOCK_DISTRIBUTOR,
            'mock-distributor-2' : MOCK_DISTRIBUTOR_2,
    }

    global GROUP_DISTRIBUTOR_MAPPINGS
    GROUP_DISTRIBUTOR_MAPPINGS = {
        'mock-group-distributor' : MOCK_GROUP_DISTRIBUTOR,
        'mock-group-distributor-2' : MOCK_GROUP_DISTRIBUTOR_2,
    }

    global IMPORTER_MAPPINGS
    IMPORTER_MAPPINGS = {
        'mock-importer' : MOCK_IMPORTER
    }

    global GROUP_IMPORTER_MAPPINGS
    GROUP_IMPORTER_MAPPINGS = {
        'mock-group-importer' : MOCK_GROUP_IMPORTER
    }

    global PROFILER_MAPPINGS
    PROFILER_MAPPINGS = {}
    for profiler in MOCK_PROFILERS:
        for t in profiler.metadata()['types']:
            PROFILER_MAPPINGS[t] = profiler

    # Return the mock instance; eventually can enhance this to support
    # multiple IDs and instances
    def mock_get_distributor_by_id(id):
        if id not in DISTRIBUTOR_MAPPINGS:
            raise plugin_exceptions.PluginNotFound()

        return DISTRIBUTOR_MAPPINGS[id], {}

    def mock_get_group_distributor_by_id(id):
        if id not in GROUP_DISTRIBUTOR_MAPPINGS:
            raise plugin_exceptions.PluginNotFound()

        return GROUP_DISTRIBUTOR_MAPPINGS[id], {}

    def mock_get_importer_by_id(id):
        if id not in IMPORTER_MAPPINGS:
            raise plugin_exceptions.PluginNotFound()

        return IMPORTER_MAPPINGS[id], {}

    def mock_get_group_importer_by_id(id):
        if id not in GROUP_IMPORTER_MAPPINGS:
            raise plugin_exceptions.PluginNotFound()

        return GROUP_IMPORTER_MAPPINGS[id], {}

    def mock_get_profiler_by_type(type):
        if type not in PROFILER_MAPPINGS:
            raise plugin_exceptions.PluginNotFound()

        return PROFILER_MAPPINGS[type], {}

    # Monkey patch in the mock methods
    plugin_api.get_distributor_by_id = mock_get_distributor_by_id
    plugin_api.get_group_distributor_by_id = mock_get_group_distributor_by_id
    plugin_api.get_importer_by_id = mock_get_importer_by_id
    plugin_api.get_group_importer_by_id = mock_get_group_importer_by_id
    plugin_api.get_profiler_by_type = mock_get_profiler_by_type

    # -- configure the mock instances -----------------------------------------

    # By default, have the plugins indicate configurations are valid
    MOCK_IMPORTER.validate_config.return_value = True, None
    MOCK_IMPORTER.sync_repo.return_value = SyncReport(True, 10, 5, 1, 'Summary of the sync', 'Details of the sync')

    MOCK_GROUP_IMPORTER.validate_config.return_value = True, None

    MOCK_DISTRIBUTOR.validate_config.return_value = True, None
    MOCK_DISTRIBUTOR.publish_repo.return_value = PublishReport(True, 'Summary of the publish', 'Details of the publish')

    MOCK_DISTRIBUTOR_2.validate_config.return_value = True, None
    MOCK_DISTRIBUTOR_2.publish_repo.return_value = PublishReport(True, 'Summary of the publish', 'Details of the publish')

    MOCK_GROUP_DISTRIBUTOR.validate_config.return_value = True, None
    MOCK_GROUP_DISTRIBUTOR_2.validate_config.return_value = True, None

    for profiler in MOCK_PROFILERS:
        profiler.update_profile = \
            mock.Mock(side_effect=lambda i,p,c,x: p)
        profiler.install_units = \
            mock.Mock(side_effect=lambda i,u,o,c,x: sorted(u))
        profiler.update_units = \
            mock.Mock(side_effect=lambda i,u,o,c,x: sorted(u))
        profiler.uninstall_units = \
            mock.Mock(side_effect=lambda i,u,o,c,x: sorted(u))
        profiler.unit_applicable = \
            mock.Mock(side_effect=lambda i,u,c,x: ApplicabilityReport(u, False, 'mocked'))

def reset():
    """
    Removes the plugin loader monkey patch.
    """

    # Reset the mock instances; reset doesn't do everything hence the manual steps
    MOCK_IMPORTER.reset_mock()
    MOCK_GROUP_IMPORTER.reset_mock()
    MOCK_DISTRIBUTOR.reset_mock()
    MOCK_DISTRIBUTOR_2.reset_mock()
    MOCK_GROUP_DISTRIBUTOR.reset_mock()
    MOCK_GROUP_DISTRIBUTOR_2.reset_mock()
    MOCK_PROFILER.reset_mock()
    MOCK_PROFILER_RPM.reset_mock()

    # Undo the monkey patch
    plugin_api.get_distributor_by_id = _ORIG_GET_DISTRIBUTOR_BY_ID
    plugin_api.get_group_distributor_by_id = _ORIG_GET_GROUP_DISTRIBUTOR_BY_ID
    plugin_api.get_importer_by_id = _ORIG_GET_IMPORTER_BY_ID
    plugin_api.get_group_importer_by_id = _ORIG_GET_GROUP_IMPORTER_BY_ID
    plugin_api.get_profiler_by_type = _ORIG_GET_PROFILER_BY_TYPE

    # Clean out the loaded plugin types
    plugin_api._MANAGER.importers.remove_plugin('mock-importer')
    plugin_api._MANAGER.group_importers.remove_plugin('mock-group-importer')
    plugin_api._MANAGER.distributors.remove_plugin('mock-distributor')
    plugin_api._MANAGER.distributors.remove_plugin('mock-distributor-2')
    plugin_api._MANAGER.group_distributors.remove_plugin('mock-group-distributor')
    plugin_api._MANAGER.group_distributors.remove_plugin('mock-group-distributor-2')
