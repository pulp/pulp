#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
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

import glob
import mock
import os
import shutil
import sys
import tempfile
import time
import unittest
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/importers/yum_importer/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/distributors/yum_distributor/")
from distributor import YumDistributor, YUM_DISTRIBUTOR_TYPE_ID, \
        REQUIRED_CONFIG_KEYS, OPTIONAL_CONFIG_KEYS, RPM_TYPE_ID, SRPM_TYPE_ID

from pulp.server.content.plugins.model import Repository, Unit

import distributor_mocks

class TestDistributor(unittest.TestCase):

    def setUp(self):
        super(TestDistributor, self).setUp()
        self.init()

    def tearDown(self):
        super(TestDistributor, self).tearDown()
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()
        #pkg_dir is where we simulate units actually residing
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        os.makedirs(self.pkg_dir)
        #publish_dir simulates /var/lib/pulp/published
        self.publish_dir = os.path.join(self.temp_dir, "publish")
        os.makedirs(self.publish_dir)
        self.repo_working_dir = os.path.join(self.temp_dir, "repo_working_dir")
        os.makedirs(self.repo_working_dir)

    def clean(self):
        shutil.rmtree(self.temp_dir)

    def get_units(self, count=5):
        units = []
        for index in range(0, count):
            u = self.get_unit()
            units.append(u)
        return units

    def get_unit(self, type_id="rpm"):
        uniq_id = uuid4()
        filename = "test_unit-%s" % (uniq_id)
        storage_path = os.path.join(self.pkg_dir, filename)
        metadata = {}
        metadata["relativepath"] = os.path.join("a/b/c", filename)
        metadata["filename"] = filename
        unit_key = uniq_id
        # Create empty file to represent the unit
        open(storage_path, "a+")
        u = Unit(type_id, unit_key, metadata, storage_path)
        return u

    def test_metadata(self):
        metadata = YumDistributor.metadata()
        self.assertEquals(metadata["id"], YUM_DISTRIBUTOR_TYPE_ID)
        self.assertTrue(RPM_TYPE_ID in metadata["types"])
        self.assertTrue(SRPM_TYPE_ID in metadata["types"])

    def test_validate_config(self):
        repo = mock.Mock(spec=Repository)
        distributor = YumDistributor()
        # Confirm that required keys are successful
        req_kwargs = {}
        for arg in REQUIRED_CONFIG_KEYS:
            req_kwargs[arg] = "sample_value"
        config = distributor_mocks.get_basic_config(**req_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertTrue(state)
        # Confirm required and optional are successful
        optional_kwargs = dict(req_kwargs)
        for arg in OPTIONAL_CONFIG_KEYS:
            if arg != "https_publish_dir":
                optional_kwargs[arg] = "sample_value"
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertTrue(state)
        # Test that config fails when a bad value for non_existing_dir is used
        optional_kwargs["https_publish_dir"] = "non_existing_dir"
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertFalse(state)
        # Test config succeeds with a good value of https_publish_dir
        optional_kwargs["https_publish_dir"] = self.temp_dir
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertTrue(state)
        del optional_kwargs["https_publish_dir"]

        # Confirm an extra key fails
        optional_kwargs["extra_arg_not_used"] = "sample_value"
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertFalse(state)
        self.assertTrue("extra_arg_not_used" in msg)

        # Confirm missing a required fails
        del optional_kwargs["extra_arg_not_used"]
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertTrue(state)

        del optional_kwargs["relative_url"]
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertFalse(state)
        self.assertTrue("relative_url" in msg)

    def test_handle_symlinks(self):
        distributor = YumDistributor()
        units = []
        symlink_dir = os.path.join(self.temp_dir, "symlinks")
        num_links = 5
        for index in range(0,num_links):
            relpath = "file_%s.rpm" % (index)
            sp = os.path.join(self.pkg_dir, relpath)
            open(sp, "a") # Create an empty file
            if index % 2 == 0:
                # Ensure we can support symlinks in subdirs
                relpath = os.path.join("a", "b", "c", relpath)
            u = Unit("rpm", "unit_key_%s" % (index), {"relativepath":relpath}, sp)
            units.append(u)

        status, errors = distributor.handle_symlinks(units, symlink_dir)
        self.assertTrue(status)
        self.assertEqual(len(errors), 0)
        for u in units:
            symlink_path = os.path.join(symlink_dir, u.metadata["relativepath"])
            self.assertTrue(os.path.exists(symlink_path))
            self.assertTrue(os.path.islink(symlink_path))
            target = os.readlink(symlink_path)
            self.assertEqual(target, u.storage_path)
        # Test republish is successful
        status, errors = distributor.handle_symlinks(units, symlink_dir)
        self.assertTrue(status)
        self.assertEqual(len(errors), 0)
        for u in units:
            symlink_path = os.path.join(symlink_dir, u.metadata["relativepath"])
            self.assertTrue(os.path.exists(symlink_path))
            self.assertTrue(os.path.islink(symlink_path))
            target = os.readlink(symlink_path)
            self.assertEqual(target, u.storage_path)
        # Simulate a package is deleted
        os.unlink(units[0].storage_path)
        status, errors = distributor.handle_symlinks(units, symlink_dir)
        self.assertFalse(status)
        self.assertEqual(len(errors), 1)


    def test_get_relpath_from_unit(self):
        distributor = YumDistributor()
        test_unit = Unit("rpm", "unit_key", {}, "")

        test_unit.storage_path = "test_0"
        rel_path = distributor.get_relpath_from_unit(test_unit)
        self.assertEqual(rel_path, "test_0")

        test_unit.metadata["fileName"] = "test_1"
        rel_path = distributor.get_relpath_from_unit(test_unit)
        self.assertEqual(rel_path, "test_1")

        test_unit.metadata["filename"] = "test_2"
        rel_path = distributor.get_relpath_from_unit(test_unit)
        self.assertEqual(rel_path, "test_2")

        test_unit.metadata["relativepath"] = "test_3"
        rel_path = distributor.get_relpath_from_unit(test_unit)
        self.assertEqual(rel_path, "test_3")


    def test_create_symlink(self):
        target_dir = os.path.join(self.temp_dir, "a", "b", "c", "d", "e")
        distributor = YumDistributor()
        # Create an empty file to serve as the source_path
        source_path = os.path.join(self.temp_dir, "some_test_file.txt")
        open(source_path, "a")
        symlink_path = os.path.join(self.temp_dir, "symlink_dir", "a", "b", "file_path.lnk")
        # Confirm subdir of symlink_path doesn't exist
        self.assertFalse(os.path.isdir(os.path.dirname(symlink_path)))
        self.assertTrue(distributor.create_symlink(source_path, symlink_path))
        # Confirm we created the subdir
        self.assertTrue(os.path.isdir(os.path.dirname(symlink_path)))
        self.assertTrue(os.path.exists(symlink_path))
        self.assertTrue(os.path.islink(symlink_path))
        # Verify the symlink points to the source_path
        a = os.readlink(symlink_path)
        self.assertEqual(a, source_path)

    def test_create_dirs(self):
        target_dir = os.path.join(self.temp_dir, "a", "b", "c", "d", "e")
        distributor = YumDistributor()
        self.assertFalse(os.path.exists(target_dir))
        self.assertTrue(distributor.create_dirs(target_dir))
        self.assertTrue(os.path.exists(target_dir))
        self.assertTrue(os.path.isdir(target_dir))
        # Test we can call it twice with no errors
        self.assertTrue(distributor.create_dirs(target_dir))
        # Remove permissions to directory and force an error
        orig_stat = os.stat(target_dir)
        try:
            os.chmod(target_dir, 0000)
            self.assertFalse(os.access(target_dir, os.R_OK))
            target_dir_b = os.path.join(target_dir, "f")
            self.assertFalse(distributor.create_dirs(target_dir_b))
        finally:
            os.chmod(target_dir, orig_stat.st_mode)

    def test_empty_publish(self):
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "test_empty_publish"
        existing_units = []
        publish_conduit = distributor_mocks.get_publish_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)
        config = distributor_mocks.get_basic_config(https_publish_dir=self.publish_dir)
        distributor = YumDistributor()
        report = distributor.publish_repo(repo, publish_conduit, config)
        self.assertTrue(report.success_flag)
        summary = report.summary
        self.assertEqual(summary["num_units_attempted"], 0)
        self.assertEqual(summary["num_units_published"], 0)
        self.assertEqual(summary["num_units_errors"], 0)
        expected_repo_publish_dir = os.path.join(self.publish_dir, "repos", repo.id)
        self.assertEqual(summary["repo_publish_dir"], expected_repo_publish_dir)
        details = report.details
        self.assertEqual(len(details["errors"]), 0)


    def test_publish(self):
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "test_publish"
        num_units = 10
        relative_url = "rel_a/rel_b/rel_c/"
        existing_units = self.get_units(count=num_units)
        publish_conduit = distributor_mocks.get_publish_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)
        config = distributor_mocks.get_basic_config(https_publish_dir=self.publish_dir, relative_url=relative_url)
        distributor = YumDistributor()
        report = distributor.publish_repo(repo, publish_conduit, config)
        self.assertTrue(report.success_flag)
        summary = report.summary
        self.assertEqual(summary["num_units_attempted"], num_units)
        self.assertEqual(summary["num_units_published"], num_units)
        self.assertEqual(summary["num_units_errors"], 0)
        expected_repo_publish_dir = os.path.join(self.publish_dir, "repos", relative_url)
        self.assertEqual(summary["repo_publish_dir"], expected_repo_publish_dir)
        details = report.details
        self.assertEqual(len(details["errors"]), 0)
        #
        # Add a verification of the publish directory
        #
        self.assertTrue(os.path.exists(summary["repo_publish_dir"]))
        self.assertTrue(os.path.islink(summary["repo_publish_dir"].rstrip("/")))
        source_of_link = os.readlink(expected_repo_publish_dir.rstrip("/"))
        self.assertEquals(source_of_link, repo.working_dir)
        #
        # Verify the expected units
        #
        for u in existing_units:
            expected_link = os.path.join(expected_repo_publish_dir, u.metadata["relativepath"])
            self.assertTrue(os.path.exists(expected_link))
            actual_target = os.readlink(expected_link)
            expected_target = u.storage_path
            self.assertEqual(actual_target, expected_target)
