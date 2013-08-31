# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import sys
import unittest

import mock

from pulp.client.extensions import loader
from pulp.client.extensions.core import PulpCli, PulpPrompt, ClientContext
from pulp.client.extensions import decorator


TEST_DIRS_ROOT = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data',
                              'extensions_loader_tests')

# Contains 4 properly structured plugins, 3 of which contain the CLI init module
VALID_SET = TEST_DIRS_ROOT + '/valid_set'

# Contains no plugins
EMPTY_SET = TEST_DIRS_ROOT + '/empty_set'

# Contains 2 plugins, 1 of which loads correct and another that fails
PARTIAL_FAIL_SET = TEST_DIRS_ROOT + '/partial_fail_set'

# Contains 1 plugin which fails the initial import step
PARTIAL_FAIL_SET_2 = TEST_DIRS_ROOT + '/partial_fail_set_2'

# Not meant to be loaded as a base directory, each should be loaded individually
# through _load_pack to verify the proper exception case is raised
INDIVIDUAL_FAIL_DIR = TEST_DIRS_ROOT + '/individual_fail_extensions'


class ExtensionLoaderTests(unittest.TestCase):

    def setUp(self):
        super(ExtensionLoaderTests, self).setUp()

        self.prompt = PulpPrompt()
        self.cli = PulpCli(self.prompt)
        self.context = ClientContext(None, None, None, self.prompt, None, cli=self.cli)

    # prevent entry points from being loaded
    @mock.patch('pkg_resources.iter_entry_points', return_value=())
    def test_load_valid_set_cli(self, mock_entry):
        """
        Tests loading the set of CLI extensions in the valid_set directory. These
        extensions have the following properties:
        * Three extensions, all of which are set up correctly to be loaded
        * Only two of them (ext1 and ext2) contain a CLI loading module
        * Each of those will add a single section to the CLI named section-X,
          where X is the number in the directory name
        """

        # Test
        loader.load_extensions(VALID_SET, self.context, 'admin')

        # Verify
        self.assertTrue(self.cli.root_section.find_subsection('section-1') is not None)
        self.assertTrue(self.cli.root_section.find_subsection('section-2') is not None)

    def test_resolve_order(self):
        """
        Tests the ordering functionality using the valid_set directory extensions.
        """

        # Test
        modules = loader._load_pack_modules(VALID_SET)
        sorted_modules = loader._resolve_order(modules)

        # Verify
        # 3 priority levels
        self.assertEqual(3, len(sorted_modules))
        self.assertEqual('ext3', sorted_modules[1][loader._MODULES][0].__name__)
        self.assertEqual('ext1', sorted_modules[5][loader._MODULES][0].__name__)
        self.assertEqual('ext4', sorted_modules[5][loader._MODULES][1].__name__)
        self.assertEqual('ext2', sorted_modules[7][loader._MODULES][0].__name__)


    def test_load_extensions_bad_dir(self):
        """
        Tests loading extensions on a directory that doesn't exist.
        """
        try:
            loader.load_extensions('fake_dir', self.context, 'admin')
        except loader.InvalidExtensionsDirectory, e:
            self.assertEqual(e.dir, 'fake_dir')
            print(e) # for coverage

    # prevent entry points from being loaded
    @mock.patch('pkg_resources.iter_entry_points', return_value=())
    def test_load_partial_fail_set_cli(self, mock_entry):
        # Test
        try:
            loader.load_extensions(PARTIAL_FAIL_SET, self.context, 'admin')
            self.fail('Exception expected')
        except loader.LoadFailed, e:
            self.assertEqual(1, len(e.failed_packs))
            self.assertTrue('init_exception' in e.failed_packs)

    def test_load_partial_fail_set_2_cli(self):
        # Test
        try:
            loader.load_extensions(PARTIAL_FAIL_SET_2, self.context, 'admin')
            self.fail('Exception expected')
        except loader.LoadFailed, e:
            self.assertEqual(1, len(e.failed_packs))
            self.assertTrue('not_python_module' in e.failed_packs)
            print(e) # for coverage

    def test_load_no_init_module(self):
        """
        Tests loading an extension pack that doesn't contain the cli init module.
        """
        if INDIVIDUAL_FAIL_DIR not in sys.path:
            sys.path.append(INDIVIDUAL_FAIL_DIR)
        mod = __import__('no_ui_hook')

        # Make sure it doesn't raise an exception
        loader._load_pack(INDIVIDUAL_FAIL_DIR, mod, self.context)

    def test_load_initialize_error(self):
        """
        Tests loading an extension that raises an error during the initialize call.
        """
        if INDIVIDUAL_FAIL_DIR not in sys.path:
            sys.path.append(INDIVIDUAL_FAIL_DIR)
        mod = __import__('init_error')

        self.assertRaises(loader.InitError, loader._load_pack, INDIVIDUAL_FAIL_DIR, mod, self.context)

    def test_load_no_init_function(self):
        """
        Tests loading an extension that doesn't have a properly defined UI hook.
        """
        if INDIVIDUAL_FAIL_DIR not in sys.path:
            sys.path.append(INDIVIDUAL_FAIL_DIR)
        mod = __import__('no_init_function')

        self.assertRaises(loader.NoInitFunction, loader._load_pack, INDIVIDUAL_FAIL_DIR, mod, self.context)

    @mock.patch('pkg_resources.iter_entry_points', autospec=True)
    def test_load_entry_points(self, mock_iter):
        # Make sure we try to load extensions through entry points.
        context = mock.MagicMock()
        entry_point = mock.MagicMock()
        mock_iter.return_value = [entry_point]

        loader.load_extensions(EMPTY_SET, context, 'admin')

        mock_iter.assert_called_once_with('pulp.extensions.admin')
        entry_point.load.assert_called_once_with()
        entry_point.load.return_value.assert_called_once_with(context)

    @mock.patch('pkg_resources.iter_entry_points', autospec=True)
    def test_entry_point_priority(self, mock_iter):
    # Make sure we load extensions in the correct order based on priority.
        class MockLoad(object):
            """
            Used to determine in what order the load() methods were called.
            """
            def __init__(self, i, order_of_calling):
                self.i = i
                self.order_of_calling = order_of_calling

            def __call__(self, *args, **kwargs):
                self.order_of_calling.append(self)
                return mock.MagicMock()

        order_of_calling = []
        context = mock.MagicMock()
        entry_point1 = decorator.priority()(mock.MagicMock())
        entry_point1.load = MockLoad(1, order_of_calling)
        entry_point2 = decorator.priority(loader.DEFAULT_PRIORITY - 10)(mock.MagicMock())
        entry_point2.load = MockLoad(2, order_of_calling)
        entry_point3 = decorator.priority(loader.DEFAULT_PRIORITY + 10)(mock.MagicMock())
        entry_point3.load = MockLoad(3, order_of_calling)
        mock_iter.return_value = [entry_point1, entry_point2, entry_point3]

        loader.load_extensions(EMPTY_SET, context, 'admin')

        self.assertEqual(len(order_of_calling), 3)
        print order_of_calling
        self.assertEqual([load.i for load in order_of_calling], [2, 1, 3])

    def test_priority_decorator(self):
        @decorator.priority(3)
        def foo():
            pass
        self.assertEqual(getattr(foo, loader.PRIORITY_VAR), 3)

    def test_priority_decorator_default_value(self):
        @decorator.priority()
        def foo():
            pass
        self.assertEqual(getattr(foo, loader.PRIORITY_VAR), loader.DEFAULT_PRIORITY)
