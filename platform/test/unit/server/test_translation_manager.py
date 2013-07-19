# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


from mock import patch, Mock

from base import PulpAsyncServerTests
from pulp.server.db.model.consumer import Consumer, UnitProfile
from pulp.server.managers import factory as managers


CONSUMER_ID = 'test_consumer'
TYPE_ID = 'test'
PROFILE = {'a': 1}
UNITS = [
    {'type_id': 'type_a', 'unit_key': {'unit_id': 'abc'}},
    {'type_id': 'type_b', 'unit_key': {'unit_id': 'def'}},
]

TRANSLATED_UNITS = [1, 2]
ALL_TRANSLATED_UNITS = TRANSLATED_UNITS * len(UNITS)


class Profiler(object):
    install_units = Mock(return_value=TRANSLATED_UNITS)
    update_units = Mock(return_value=TRANSLATED_UNITS)
    uninstall_units = Mock(return_value=TRANSLATED_UNITS)


class TranslationManagerTests(PulpAsyncServerTests):

    def setUp(self):
        super(self.__class__, self).setUp()
        Consumer.get_collection().remove()
        manager = managers.consumer_manager()
        manager.register(CONSUMER_ID)
        manager = managers.consumer_profile_manager()
        manager.create(CONSUMER_ID, TYPE_ID, PROFILE)

    def tearDown(self):
        super(self.__class__, self).tearDown()
        Consumer.get_collection().remove()
        UnitProfile.get_collection().remove()

    @patch('pulp.plugins.loader.api.get_profiler_by_type')
    def test_install(self, plugins_mock):
        profiler = Profiler()
        plugins_mock.return_value = profiler, {}
        manager = managers.consumer_content_translation_manager()
        units = manager.install_units(CONSUMER_ID, UNITS, {})
        self.assertTrue(profiler.install_units.called)
        self.assertEqual(units, ALL_TRANSLATED_UNITS)

    @patch('pulp.plugins.loader.api.get_profiler_by_type')
    def test_update(self, plugins_mock):
        profiler = Profiler()
        plugins_mock.return_value = profiler, {}
        manager = managers.consumer_content_translation_manager()
        units = manager.update_units(CONSUMER_ID, UNITS, {})
        self.assertTrue(profiler.update_units.called)
        self.assertEqual(units, ALL_TRANSLATED_UNITS)

    @patch('pulp.plugins.loader.api.get_profiler_by_type')
    def test_uninstall(self, plugins_mock):
        profiler = Profiler()
        plugins_mock.return_value = profiler, {}
        manager = managers.consumer_content_translation_manager()
        units = manager.uninstall_units(CONSUMER_ID, UNITS, {})
        self.assertTrue(profiler.uninstall_units.called)
        self.assertEqual(units, ALL_TRANSLATED_UNITS)

