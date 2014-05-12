# -*- coding: utf-8 -*-
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

import unittest
import os
import shutil
import tempfile

from mock import Mock

from pulp.devel.unit import util


class TestCompareDic(unittest.TestCase):

    def test_compare_dict_equality(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """
        source = {'foo': 'bar', 'baz': 'qux'}
        util.compare_dict(source, source)

    def test_compare_dict_inequality_keys(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """
        source = {'foo': 'bar', 'baz': 'qux'}
        target = {'quack': 'duck'}
        self.assertRaises(AssertionError, util.compare_dict, source, target)

    def test_compare_dict_inequality_values(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """
        source = {'foo': 'bar', 'baz': 'qux'}
        target = {'foo': 'bar', 'baz': 'duck'}
        self.assertRaises(AssertionError, util.compare_dict, source, target)

    def test_compare_dict_source_not_dict(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """
        source = 'foo'
        target = {'foo': 'bar', 'baz': 'duck'}
        self.assertRaises(AssertionError, util.compare_dict, source, target)

    def test_compare_dict_target_not_dict(self):
        """
        Tests the correct API in the bindings is replaced by the simulator.
        """
        source = {'foo': 'bar', 'baz': 'qux'}
        target = 'bar'
        self.assertRaises(AssertionError, util.compare_dict, source, target)


class TestAssertBodyMatchesAsyncTask(unittest.TestCase):

    def test_successful_match(self):
        body = {'spawned_tasks': [{'task_id': "foo"}, ]}
        task = Mock()
        task.id = "foo"
        util.assert_body_matches_async_task(body, task)

    def test_failure_malformed_body(self):
        body = {}
        task = Mock()
        task.id = "foo"
        self.assertRaises(Exception, util.assert_body_matches_async_task, body, task)


class TestTouch(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.working_dir, ignore_errors=True)

    def test_in_existing_directory(self):
        filename = os.path.join(self.working_dir, "foo.txt")
        util.touch(filename)

        self.assertTrue(os.path.exists(filename))

    def test_create_parent_diectory(self):
        filename = os.path.join(self.working_dir, 'subdir', "foo.txt")
        util.touch(filename)
        self.assertTrue(os.path.exists(filename))
