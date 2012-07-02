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

import pulp.plugins.loader as plugin_loader
from pulp.plugins.model import SyncReport, PublishReport

# -- constants ----------------------------------------------------------------

# Used when reverting the monkey patch
_ORIG_GET_DISTRIBUTOR_BY_ID = None
_ORIG_GET_IMPORTER_BY_ID = None
_ORIG_GET_PROFILER_BY_TYPE = None

# -- plugin classes -----------------------------------------------------------

class MockImporter(mock.Mock):

    @classmethod
    def metadata(cls):
        return {'types' : ['mock-type']}

class MockDistributor(mock.Mock):

    @classmethod
    def metadata(cls):
        return {'types' : ['mock-type']}

class MockProfiler(mock.Mock):

    @classmethod
    def metadata(cls):
        return {'types' : ['mock-type', 'type-1', 'rpm']}

# -- mock instances -----------------------------------------------------------

MOCK_IMPORTER = MockImporter()
MOCK_DISTRIBUTOR = MockDistributor()
MOCK_DISTRIBUTOR_2 = MockDistributor()
MOCK_PROFILER = MockProfiler()

# Set by install; can edit these during a test to simulate a plugin being uninstalled
DISTRIBUTOR_MAPPINGS = None
IMPORTER_MAPPINGS = None
PROFILER_MAPPINGS = None

# -- public -------------------------------------------------------------------

def install():
    """
    Called during test setup to monkey patch the plugin loader for testing.
    """

    # -- update plugin loader inventory ---------------------------------------

    plugin_loader._create_loader()

    plugin_loader._LOADER.add_importer('mock-importer', MockImporter, {})
    plugin_loader._LOADER.add_distributor('mock-distributor', MockDistributor, {})
    plugin_loader._LOADER.add_distributor('mock-distributor-2', MockDistributor, {})
    plugin_loader._LOADER.add_profiler('mock-profiler', MockProfiler, {})

    # -- return mock instances instead of ephemeral ones ----------------------

    # Save the state of the original plugin loader so it can be reverted
    global _ORIG_GET_DISTRIBUTOR_BY_ID
    global _ORIG_GET_IMPORTER_BY_ID
    global _ORIG_GET_PROFILER_BY_TYPE

    _ORIG_GET_DISTRIBUTOR_BY_ID = plugin_loader.get_distributor_by_id
    _ORIG_GET_IMPORTER_BY_ID = plugin_loader.get_importer_by_id
    _ORIG_GET_PROFILER_BY_TYPE = plugin_loader.get_profiler_by_type

    # Setup the importer/distributor mappings that return the mock instances
    global DISTRIBUTOR_MAPPINGS
    DISTRIBUTOR_MAPPINGS = {
            'mock-distributor' : MOCK_DISTRIBUTOR,
            'mock-distributor-2' : MOCK_DISTRIBUTOR_2,
    }

    global IMPORTER_MAPPINGS
    IMPORTER_MAPPINGS = {
        'mock-importer' : MOCK_IMPORTER
    }

    global PROFILER_MAPPINGS
    PROFILER_MAPPINGS = {
        'rpm' : MOCK_PROFILER
    }

    # Return the mock instance; eventually can enhance this to support
    # multiple IDs and instances
    def mock_get_distributor_by_id(id):
        if id not in DISTRIBUTOR_MAPPINGS:
            raise plugin_loader.PluginNotFound()

        return DISTRIBUTOR_MAPPINGS[id], {}

    def mock_get_importer_by_id(id):
        if id not in IMPORTER_MAPPINGS:
            raise plugin_loader.PluginNotFound()

        return IMPORTER_MAPPINGS[id], {}

    def mock_get_profiler_by_type(type):
        if type not in PROFILER_MAPPINGS:
            raise plugin_loader.PluginNotFound()

        return PROFILER_MAPPINGS[type], {}

    # Monkey patch in the mock methods
    plugin_loader.get_distributor_by_id = mock_get_distributor_by_id
    plugin_loader.get_importer_by_id = mock_get_importer_by_id
    plugin_loader.get_profiler_by_type = mock_get_profiler_by_type

    # -- configure the mock instances -----------------------------------------

    # By default, have the plugins indicate configurations are valid
    MOCK_IMPORTER.validate_config.return_value = True
    MOCK_IMPORTER.sync_repo.return_value = SyncReport(True, 10, 5, 1, 'Summary of the sync', 'Details of the sync')

    MOCK_DISTRIBUTOR.validate_config.return_value = True
    MOCK_DISTRIBUTOR.publish_repo.return_value = PublishReport(True, 'Summary of the publish', 'Details of the publish')

    MOCK_DISTRIBUTOR_2.validate_config.return_value = True
    MOCK_DISTRIBUTOR_2.publish_repo.return_value = PublishReport(True, 'Summary of the publish', 'Details of the publish')

    MOCK_PROFILER.update_profile = lambda i,p,c,x: p
    MOCK_PROFILER.install_units = lambda i,u,o,c,x: sorted(u)
    MOCK_PROFILER.update_units = lambda i,u,o,c,x: sorted(u)
    MOCK_PROFILER.uninstall_units = lambda i,u,o,c,x: sorted(u)

def reset():
    """
    Removes the plugin loader monkey patch.
    """

    # Reset the mock instances; reset doesn't do everything hence the manual steps
    MOCK_IMPORTER.reset_mock()
    MOCK_DISTRIBUTOR.reset_mock()
    MOCK_DISTRIBUTOR_2.reset_mock()
    MOCK_PROFILER.reset_mock()

    # Undo the monkey patch
    plugin_loader.get_distributor_by_id = _ORIG_GET_DISTRIBUTOR_BY_ID
    plugin_loader.get_importer_by_id = _ORIG_GET_IMPORTER_BY_ID
    plugin_loader.get_profiler_by_type = _ORIG_GET_PROFILER_BY_TYPE

    # Clean out the loaded plugin types
    plugin_loader._LOADER.remove_importer('mock-importer')
    plugin_loader._LOADER.remove_distributor('mock-distributor')
    plugin_loader._LOADER.remove_distributor('mock-distributor-2')
    plugin_loader._LOADER.remove_distributor('mock-profiler')