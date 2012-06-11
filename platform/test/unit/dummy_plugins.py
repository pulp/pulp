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

"""
Contains dummy importer and distributor implementations.

These play with the dispatch package better than the mock_plugins. Use this
module instead when testing with new v2 controllers that have been integrated
with dispatch.
"""

from pulp.server.content import loader as plugin_loader
from pulp.server.content.plugins.model import SyncReport, PublishReport

# dummy base class -------------------------------------------------------------

class DummyObject(object):

    def __init__(self):
        self.reset_dummy()

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.args = args
        self.kwargs = kwargs
        cls = self.__class__
        return cls()

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]
        cls = self.__class__
        return cls()

    def reset_dummy(self):
        self.call_count = 0
        self.args = []
        self.kwargs = {}

# dummy plugins ----------------------------------------------------------------

class DummyPlugin(DummyObject):

    @classmethod
    def metadata(cls):
        return {'types': ['dummy-type']}

    def validate_config(self, *args, **kwargs):
        return True


class DummyImporter(DummyPlugin):

    def sync_repo(self, *args, **kwargs):
        return SyncReport(True, 10, 5, 1, 'Summary of the sync', 'Details of the sync')


class DummyDistributor(DummyPlugin):

    def publish_repo(self, *args, **kwargs):
        return PublishReport(True, 'Summary of the publish', 'Details of the publish')

# dummy instances --------------------------------------------------------------

DUMMY_IMPORTER = DummyImporter()
DUMMY_DISTRIBUTOR = DummyDistributor()
DUMMY_DISTRIBUTOR_2 = DummyDistributor()

IMPORTER_MAPPINGS = None
DISTRIBUTOR_MAPPINGS = None

# install/reset plugins --------------------------------------------------------

# used to undo monkey patching
_ORIG_GET_IMPORTER_BY_ID = None
_ORIG_GET_DISTRIBUTOR_BY_ID = None


def install():
    """
    Install the plugin loader monkey patch dummy plugins for testing.
    """
    global DUMMY_IMPORTER, DUMMY_DISTRIBUTOR, DUMMY_DISTRIBUTOR_2, \
           IMPORTER_MAPPINGS, DISTRIBUTOR_MAPPINGS, \
           _ORIG_GET_IMPORTER_BY_ID, _ORIG_GET_DISTRIBUTOR_BY_ID

    # update plugin loader inventory

    plugin_loader._create_loader()
    plugin_loader._LOADER.add_importer('dummy-importer', DummyImporter, {})
    plugin_loader._LOADER.add_distributor('dummy-distributor', DummyDistributor, {})
    plugin_loader._LOADER.add_distributor('dummy-distributor-2', DummyDistributor, {})

    # setup the importer/distributor mappings that return the dummy instances

    IMPORTER_MAPPINGS = {'dummy-importer': DUMMY_IMPORTER}
    DISTRIBUTOR_MAPPINGS = {'dummy-distributor': DUMMY_DISTRIBUTOR,
                            'dummy-distributor-2': DUMMY_DISTRIBUTOR_2}

    # save state of original plugin so it can be reverted

    _ORIG_GET_IMPORTER_BY_ID = plugin_loader.get_importer_by_id
    _ORIG_GET_DISTRIBUTOR_BY_ID = plugin_loader.get_distributor_by_id

    # monkey-patch methods to return the dummy instances

    def dummy_get_importer_by_id(id):
        if id not in IMPORTER_MAPPINGS:
            raise plugin_loader.PluginNotFound()
        return IMPORTER_MAPPINGS[id], {}

    def dummy_get_distributor_by_id(id):
        if id not in DISTRIBUTOR_MAPPINGS:
            raise plugin_loader.PluginNotFound()
        return DISTRIBUTOR_MAPPINGS[id], {}

    # monkey-patch in the dummy methods

    plugin_loader.get_importer_by_id = dummy_get_importer_by_id
    plugin_loader.get_distributor_by_id = dummy_get_distributor_by_id


def reset():
    """
    Removes the plugin loader monkey patch and resets the dummy instances.
    """

    # reset the dummy instances

    DUMMY_IMPORTER.reset_dummy()
    DUMMY_DISTRIBUTOR.reset_dummy()
    DUMMY_DISTRIBUTOR_2.reset_dummy()

    # undo the monkey-patch

    plugin_loader.get_importer_by_id = _ORIG_GET_IMPORTER_BY_ID
    plugin_loader.get_distributor_by_id = _ORIG_GET_DISTRIBUTOR_BY_ID

    # remove the loaded plugins

    plugin_loader._LOADER.remove_importer('dummy-importer')
    plugin_loader._LOADER.remove_distributor('dummy-distributor')
    plugin_loader._LOADER.remove_distributor('dummy-distributor-2')


