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

import os
import shutil
import tempfile
import unittest

from pulp_puppet.common.model import Module
from pulp_puppet.importer import metadata

# -- constants ----------------------------------------------------------------

DATA_DIR = os.path.abspath(os.path.dirname(__file__)) + '/../data'

# -- test cases ---------------------------------------------------------------

class SuccessfulMetadataTests(unittest.TestCase):

    def setUp(self):
        self.author = 'jdob'
        self.name = 'valid'
        self.version = '1.0.0'

        self.module = Module(self.name, self.version, self.author)

        self.module_dir = os.path.join(DATA_DIR, 'good-modules', 'jdob-valid', 'pkg')
        self.tmp_dir = tempfile.mkdtemp(prefix='puppet-metadata-tests')

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_extract_metadata(self):
        # Setup
        filename = os.path.join(self.module_dir, self.module.filename())

        # Test
        metadata.extract_metadata(self.module, filename, self.tmp_dir)

        # Verify
        self.assertEqual(self.module.name, 'valid')
        self.assertEqual(self.module.version, '1.0.0')
        self.assertEqual(self.module.author, 'jdob')

        self._assert_test_module_metadata()

    def test_extract_metadata_non_standard_packaging(self):
        # Setup
        self.module = Module('misnamed', '1.0.0', 'ldob')
        self.module_dir = os.path.join(DATA_DIR, 'bad-modules')
        filename = os.path.join(self.module_dir, self.module.filename())

        # Test
        metadata.extract_metadata(self.module, filename, self.tmp_dir)

        # Verify - contains the same module as jdob-valid-1.0.0, so this is safe
        self.assertEqual(self.module.name, 'misnamed')
        self.assertEqual(self.module.version, '1.0.0')
        self.assertEqual(self.module.author, 'ldob')

        self._assert_test_module_metadata()

        extraction_root = os.path.join(self.tmp_dir, self.module.author)
        self.assertTrue(not os.path.exists(extraction_root))

    def _assert_test_module_metadata(self):

        # Assumes the content in jdob-valid-1.0.0

        self.assertEqual(self.module.source, 'http://example.org/jdob-valid/source')
        self.assertEqual(self.module.license, 'Apache License, Version 2.0')
        self.assertEqual(self.module.summary, 'Valid Module Summary')
        self.assertEqual(self.module.description, 'Valid Module Description')
        self.assertEqual(self.module.project_page, 'http://example.org/jdob-valid')

        self.assertEqual(2, len(self.module.dependencies))
        sorted_deps = sorted(self.module.dependencies, key=lambda x : x['name'])
        self.assertEqual(sorted_deps[0]['name'], 'jdob/dep-alpha')
        self.assertEqual(sorted_deps[0]['version_requirement'], '>= 1.0.0')
        self.assertEqual(sorted_deps[1]['name'], 'ldob/dep-beta')
        self.assertEqual(sorted_deps[1]['version_requirement'], '>= 2.0.0')

        self.assertEqual(self.module.types, [])

        expected_checksums = {
            'Modulefile': '704cecf2957448dcf7fa20cffa2cf7c1',
            'README': '11edd8578497566d8054684a8c89c6cb',
            'manifests/init.pp': '1d1fb26825825b4d64d37d377016869e',
            'spec/spec_helper.rb': 'a55d1e6483344f8ec6963fcb2c220372',
            'tests/init.pp': '7043c7ef0c4b0ac52b4ec6bb76008ebd'
        }
        self.assertEqual(self.module.checksums, expected_checksums)


class NegativeMetadataTests(unittest.TestCase):

    def setUp(self):
        self.author = 'jdob'
        self.name = None # set in test itself
        self.version = '1.0.0'

        self.module = Module(self.name, self.version, self.author)

        self.module_dir = os.path.join(DATA_DIR, 'bad-modules')
        self.tmp_dir = tempfile.mkdtemp(prefix='puppet-metadata-tests')

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_extract_metadata_bad_tarball(self):
        # Setup
        self.module.name = 'empty'
        filename = os.path.join(self.module_dir, self.module.filename())

        # Test
        try:
            metadata.extract_metadata(self.module, filename, self.tmp_dir)
            self.fail()
        except metadata.ExtractionException, e:
            self.assertEqual(e.module_filename, filename)

    def test_extract_non_standard_bad_tarball(self):
        # Setup
        self.module.name = 'empty'
        filename = os.path.join(self.module_dir, self.module.filename())

        # Test
        try:
            metadata._extract_non_standard_json(self.module, filename, self.tmp_dir)
            self.fail()
        except metadata.ExtractionException, e:
            self.assertEqual(e.module_filename, filename)

    def test_extract_metadata_no_metadata(self):
        # Setup
        self.module.name = 'no-metadata'
        filename = os.path.join(self.module_dir, self.module.filename())

        # Test
        try:
            metadata.extract_metadata(self.module, filename, self.tmp_dir)
            self.fail()
        except metadata.MissingModuleFile, e:
            self.assertEqual(e.module_filename, filename)