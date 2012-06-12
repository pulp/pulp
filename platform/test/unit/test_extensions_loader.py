#!/usr/bin/python
#
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

# Python
import os
import sys
import unittest

from pulp.client.extensions import loader
from pulp.client.extensions.core import PulpCli, PulpPrompt, ClientContext

# -- test data ----------------------------------------------------------------

TEST_DIRS_ROOT = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'extensions_loader_tests')

# Contains 4 properly structured plugins, 3 of which contain the CLI init module
VALID_SET = TEST_DIRS_ROOT + '/valid_set'

# Contains 2 plugins, 1 of which loads correct and another that fails
PARTIAL_FAIL_SET = TEST_DIRS_ROOT + '/partial_fail_set'

# Contains 1 plugin which fails the initial import step
PARTIAL_FAIL_SET_2 = TEST_DIRS_ROOT + '/partial_fail_set_2'

# Not meant to be loaded as a base directory, each should be loaded individually
# through _load_pack to verify the proper exception case is raised
INDIVIDUAL_FAIL_DIR = TEST_DIRS_ROOT + '/individual_fail_extensions'

# -- test cases ---------------------------------------------------------------

class ExtensionLoaderTests(unittest.TestCase):

    def setUp(self):
        super(ExtensionLoaderTests, self).setUp()

        self.prompt = PulpPrompt()
        self.cli = PulpCli(self.prompt)
        self.context = ClientContext(None, None, None, self.prompt, None, cli=self.cli)

    def test_load_valid_set_cli(self):
        """
        Tests loading the set of CLI extensions in the valid_set directory. These
        extensions have the following properties:
        * Three extensions, all of which are set up correctly to be loaded
        * Only two of them (ext1 and ext2) contain a CLI loading module
        * Each of those will add a single section to the CLI named section-X,
          where X is the number in the directory name
        """

        # Test
        loader.load_extensions(VALID_SET, self.context)

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
        self.assertEqual(4, len(sorted_modules))
        self.assertEqual('ext3', sorted_modules[0].__name__)
        self.assertEqual('ext1', sorted_modules[1].__name__)
        self.assertEqual('ext4', sorted_modules[2].__name__)
        self.assertEqual('ext2', sorted_modules[3].__name__)


    def test_load_extensions_bad_dir(self):
        """
        Tests loading extensions on a directory that doesn't exist.
        """
        try:
            loader.load_extensions('fake_dir', self.context)
        except loader.InvalidExtensionsDirectory, e:
            self.assertEqual(e.dir, 'fake_dir')
            print(e) # for coverage

    def test_load_partial_fail_set_cli(self):
        # Test
        try:
            loader.load_extensions(PARTIAL_FAIL_SET, self.context)
            self.fail('Exception expected')
        except loader.LoadFailed, e:
            self.assertEqual(1, len(e.failed_packs))
            self.assertTrue('init_exception' in e.failed_packs)

    def test_load_partial_fail_set_2_cli(self):
        # Test
        try:
            loader.load_extensions(PARTIAL_FAIL_SET_2, self.context)
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
