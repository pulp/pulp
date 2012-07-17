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

import mock
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/distributors/")

from yum_distributor.distributor import YumDistributor, YUM_DISTRIBUTOR_TYPE_ID,\
    RPM_TYPE_ID, SRPM_TYPE_ID
from pulp_rpm.yum_plugin import util
from pulp.plugins.model import RelatedRepository, Repository, Unit
from pulp.plugins.config import PluginCallConfiguration

import distributor_mocks
import rpm_support_base

class TestDistributor(rpm_support_base.PulpRPMTests):

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
        self.http_publish_dir = os.path.join(self.temp_dir, "publish", "http")
        os.makedirs(self.http_publish_dir)

        self.https_publish_dir = os.path.join(self.temp_dir, "publish", "https")
        os.makedirs(self.https_publish_dir)

        self.repo_working_dir = os.path.join(self.temp_dir, "repo_working_dir")
        os.makedirs(self.repo_working_dir)
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "./data"))

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
        repo.id = "testrepo"
        distributor = YumDistributor()
        distributor.process_repo_auth_certificate_bundle = mock.Mock()
        # Confirm that required keys are successful
        req_kwargs = {}
        req_kwargs['http'] = True
        req_kwargs['https'] = False
        req_kwargs['relative_url'] = "sample_value"
        config = distributor_mocks.get_basic_config(**req_kwargs)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)
        # Confirm required and optional are successful
        optional_kwargs = dict(req_kwargs)
        optional_kwargs['auth_ca'] = open(os.path.join(self.data_dir, "valid_ca.crt")).read()
        optional_kwargs['https_ca'] = open(os.path.join(self.data_dir, "valid_ca.crt")).read()
        optional_kwargs['protected'] = True
        optional_kwargs['generate_metadata'] = True
        optional_kwargs['checksum_type'] = "sha"
        optional_kwargs['skip'] = []
        optional_kwargs['auth_cert'] = open(os.path.join(self.data_dir, "cert.crt")).read()
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)
        # Test that config fails when a bad value for non_existing_dir is used
        optional_kwargs["http_publish_dir"] = "non_existing_dir"
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)
        # Test config succeeds with a good value of https_publish_dir
        optional_kwargs["http_publish_dir"] = self.temp_dir
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)
        del optional_kwargs["http_publish_dir"]
        # Test that config fails when a bad value for non_existing_dir is used
        optional_kwargs["https_publish_dir"] = "non_existing_dir"
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)
        # Test config succeeds with a good value of https_publish_dir
        optional_kwargs["https_publish_dir"] = self.temp_dir
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)
        del optional_kwargs["https_publish_dir"]

        # Confirm an extra key fails
        optional_kwargs["extra_arg_not_used"] = "sample_value"
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)
        self.assertTrue("extra_arg_not_used" in msg)

        # Confirm missing a required fails
        del optional_kwargs["extra_arg_not_used"]
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)

        del optional_kwargs["relative_url"]
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config, [])
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

        test_unit.unit_key = {"fileName" : "test_1"}
        rel_path = util.get_relpath_from_unit(test_unit)
        self.assertEqual(rel_path, "test_1")

        test_unit.unit_key = {}
        test_unit.storage_path = "test_0"
        rel_path = util.get_relpath_from_unit(test_unit)
        self.assertEqual(rel_path, "test_0")

        test_unit.metadata["filename"] = "test_2"
        rel_path = util.get_relpath_from_unit(test_unit)
        self.assertEqual(rel_path, "test_2")

        test_unit.metadata["relativepath"] = "test_3"
        rel_path = util.get_relpath_from_unit(test_unit)
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
        self.assertTrue(util.create_symlink(source_path, symlink_path))
        # Confirm we created the subdir
        self.assertTrue(os.path.isdir(os.path.dirname(symlink_path)))
        self.assertTrue(os.path.exists(symlink_path))
        self.assertTrue(os.path.islink(symlink_path))
        # Verify the symlink points to the source_path
        a = os.readlink(symlink_path)
        self.assertEqual(a, source_path)

    def test_create_dirs(self):
        if os.geteuid() == 0:
            # skip if run as root
            return
        target_dir = os.path.join(self.temp_dir, "a", "b", "c", "d", "e")
        distributor = YumDistributor()
        self.assertFalse(os.path.exists(target_dir))
        self.assertTrue(util.create_dirs(target_dir))
        self.assertTrue(os.path.exists(target_dir))
        self.assertTrue(os.path.isdir(target_dir))
        # Test we can call it twice with no errors
        self.assertTrue(util.create_dirs(target_dir))
        # Remove permissions to directory and force an error
        orig_stat = os.stat(target_dir)
        try:
            os.chmod(target_dir, 0000)
            self.assertFalse(os.access(target_dir, os.R_OK))
            target_dir_b = os.path.join(target_dir, "f")
            self.assertFalse(util.create_dirs(target_dir_b))
        finally:
            os.chmod(target_dir, orig_stat.st_mode)

    def test_empty_publish(self):
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "test_empty_publish"
        existing_units = []
        publish_conduit = distributor_mocks.get_publish_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)
        config = distributor_mocks.get_basic_config(https_publish_dir=self.https_publish_dir, http_publish_dir=self.http_publish_dir,
                http=True, https=True)
        distributor = YumDistributor()
        report = distributor.publish_repo(repo, publish_conduit, config)
        self.assertTrue(report.success_flag)
        summary = report.summary
        self.assertEqual(summary["num_package_units_attempted"], 0)
        self.assertEqual(summary["num_package_units_published"], 0)
        self.assertEqual(summary["num_package_units_errors"], 0)
        expected_repo_https_publish_dir = os.path.join(self.https_publish_dir, repo.id).rstrip('/')
        expected_repo_http_publish_dir = os.path.join(self.http_publish_dir, repo.id).rstrip('/')
        self.assertEqual(summary["https_publish_dir"], expected_repo_https_publish_dir)
        self.assertEqual(summary["http_publish_dir"], expected_repo_http_publish_dir)
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
        config = distributor_mocks.get_basic_config(https_publish_dir=self.https_publish_dir, relative_url=relative_url,
                http=False, https=True)
        distributor = YumDistributor()
        distributor.process_repo_auth_certificate_bundle = mock.Mock()
        status, msg = distributor.validate_config(repo, config, None)
        self.assertTrue(status)
        report = distributor.publish_repo(repo, publish_conduit, config)
        self.assertTrue(report.success_flag)
        summary = report.summary
        self.assertEqual(summary["num_package_units_attempted"], num_units)
        self.assertEqual(summary["num_package_units_published"], num_units)
        self.assertEqual(summary["num_package_units_errors"], 0)
        # Verify we did not attempt to publish to http
        expected_repo_http_publish_dir = os.path.join(self.http_publish_dir, relative_url)
        self.assertFalse(os.path.exists(expected_repo_http_publish_dir))

        expected_repo_https_publish_dir = os.path.join(self.https_publish_dir, relative_url).rstrip('/')
        self.assertEqual(summary["https_publish_dir"], expected_repo_https_publish_dir)
        self.assertTrue(os.path.exists(expected_repo_https_publish_dir))
        details = report.details
        self.assertEqual(len(details["errors"]), 0)
        #
        # Add a verification of the publish directory
        #
        self.assertTrue(os.path.exists(summary["https_publish_dir"]))
        self.assertTrue(os.path.islink(summary["https_publish_dir"].rstrip("/")))
        source_of_link = os.readlink(expected_repo_https_publish_dir.rstrip("/"))
        self.assertEquals(source_of_link, repo.working_dir)
        #
        # Verify the expected units
        #
        for u in existing_units:
            expected_link = os.path.join(expected_repo_https_publish_dir, u.metadata["relativepath"])
            self.assertTrue(os.path.exists(expected_link))
            actual_target = os.readlink(expected_link)
            expected_target = u.storage_path
            self.assertEqual(actual_target, expected_target)
        #
        # Now test flipping so https is disabled and http is enabled
        #
        config = distributor_mocks.get_basic_config(https_publish_dir=self.https_publish_dir, 
                http_publish_dir=self.http_publish_dir, relative_url=relative_url, http=True, https=False)
        report = distributor.publish_repo(repo, publish_conduit, config)
        self.assertTrue(report.success_flag)
        # Verify we did publish to http
        self.assertTrue(os.path.exists(expected_repo_http_publish_dir))

        # Verify we did not publish to https
        self.assertFalse(os.path.exists(expected_repo_https_publish_dir))

        # Verify we cleaned up the misc dirs under the https dir
        self.assertEquals(len(os.listdir(self.https_publish_dir)), 0)

    def test_split_path(self):
        distributor = YumDistributor()
        test_path = "/a"
        pieces = distributor.split_path(test_path)
        self.assertEqual(len(pieces), 1)
        self.assertTrue(pieces[0], test_path)

        test_path = "/a/"
        pieces = distributor.split_path(test_path)
        self.assertEqual(len(pieces), 1)
        self.assertTrue(pieces[0], test_path)

        test_path = "/a"
        pieces = distributor.split_path(test_path)
        self.assertEqual(len(pieces), 1)
        self.assertTrue(pieces[0], test_path)

        test_path = "a/"
        pieces = distributor.split_path(test_path)
        self.assertEqual(len(pieces), 1)
        self.assertTrue(pieces[0], test_path)

        test_path = "/a/bcde/f/ghi/j"
        pieces = distributor.split_path(test_path)
        self.assertEqual(len(pieces), 5)
        self.assertTrue(os.path.join(*pieces), test_path)

        test_path = "a/bcde/f/ghi/j"
        pieces = distributor.split_path(test_path)
        self.assertEqual(len(pieces), 5)
        self.assertTrue(os.path.join(*pieces), test_path)

        test_path = "a/bcde/f/ghi/j/"
        pieces = distributor.split_path(test_path)
        self.assertEqual(len(pieces), 5)
        self.assertTrue(os.path.join(*pieces), test_path)

        test_path = "/a/bcde/f/ghi/j/"
        pieces = distributor.split_path(test_path)
        self.assertEqual(len(pieces), 5)
        self.assertTrue(os.path.join(*pieces), test_path)

    def test_form_rel_url_lookup_table(self):
        distributor = YumDistributor()
        existing_urls = distributor.form_rel_url_lookup_table(None)
        self.assertEqual(existing_urls, {})

        url_a = "/abc/de/fg/"
        config_a = PluginCallConfiguration({"relative_url":url_a}, {})
        repo_a = RelatedRepository("repo_a_id", [config_a])

        conflict_url_a = "/abc/de/"
        conflict_config_a = PluginCallConfiguration({"relative_url":conflict_url_a}, {})
        conflict_repo_a = RelatedRepository("conflict_repo_id_a", [conflict_config_a])

        url_b = "/abc/de/kj/"
        config_b = PluginCallConfiguration({"relative_url":url_b}, {})
        repo_b = RelatedRepository("repo_b_id", [config_b])
        repo_b_dup = RelatedRepository("repo_b_dup_id", [config_b])

        url_c = "/abc/jk/fg/gfgf/gfgf/gfre/"
        config_c = PluginCallConfiguration({"relative_url":url_c}, {})
        repo_c = RelatedRepository("repo_c_id", [config_c])

        url_d = "simple"
        config_d = PluginCallConfiguration({"relative_url":url_d}, {})
        repo_d = RelatedRepository("repo_d_id", [config_d])

        url_e = ""
        config_e = PluginCallConfiguration({"relative_url":url_e}, {})
        repo_e = RelatedRepository("repo_e_id", [config_e])

        url_f = "/foo"
        config_f = PluginCallConfiguration({"relative_url":url_f}, {})
        repo_f = RelatedRepository("repo_f_id", [config_f])

        conflict_url_f = "foo/"
        conflict_config_f = PluginCallConfiguration({"relative_url":conflict_url_f}, {})
        conflict_repo_f = RelatedRepository("conflict_repo_f_id", [conflict_config_f])

        url_g = "bar/"
        config_g = PluginCallConfiguration({"relative_url":url_g}, {})
        repo_g = RelatedRepository("repo_g_id", [config_g])

        # Try with url set to None
        url_h = None
        config_h = PluginCallConfiguration({"relative_url":url_h}, {})
        repo_h = RelatedRepository("repo_h_id", [config_h])

        # Try with relative_url not existing
        config_i = PluginCallConfiguration({}, {})
        repo_i = RelatedRepository("repo_i_id", [config_i])

        existing_urls = distributor.form_rel_url_lookup_table([repo_a, repo_d, repo_e, repo_f, repo_g, repo_h])
        self.assertEqual(existing_urls, {'simple': {'repo_id': repo_d.id, 'url': url_d}, 
            'abc': {'de': {'fg': {'repo_id': repo_a.id, 'url': url_a}}}, 
            repo_e.id : {'repo_id': repo_e.id, 'url': repo_e.id}, # url_e is empty so we default to use repo id
            repo_h.id : {'repo_id': repo_h.id, 'url': repo_h.id}, # urk_h is None so we default to use repo id
            'bar': {'repo_id': repo_g.id, 'url':url_g}, 'foo': {'repo_id': repo_f.id, 'url': url_f}})

        existing_urls = distributor.form_rel_url_lookup_table([repo_a])
        self.assertEqual(existing_urls, {'abc': {'de': {'fg': {'repo_id': repo_a.id, 'url': url_a}}}})

        existing_urls = distributor.form_rel_url_lookup_table([repo_a, repo_b])
        self.assertEqual(existing_urls, {'abc': {'de': {'kj': {'repo_id': repo_b.id, 'url': url_b}, 'fg': {'repo_id': repo_a.id, 'url': url_a}}}})

        existing_urls = distributor.form_rel_url_lookup_table([repo_a, repo_b, repo_c])
        self.assertEqual(existing_urls, {'abc': {'de': {'kj': {'repo_id': repo_b.id, 'url':url_b}, 
            'fg': {'repo_id': repo_a.id, 'url':url_a}}, 'jk': {'fg': {'gfgf': {'gfgf': {'gfre': {'repo_id': repo_c.id, 'url':url_c}}}}}}})

        # Add test for exception on duplicate with repos passed in
        caught = False
        try:
            existing_urls = distributor.form_rel_url_lookup_table([repo_a, repo_b, repo_b_dup, repo_c])
        except Exception, e:
            caught = True
        self.assertTrue(caught)

        caught = False
        try:
            existing_urls = distributor.form_rel_url_lookup_table([repo_f, conflict_repo_f])
        except Exception, e:
            caught = True
        self.assertTrue(caught)

        # Add test for exception on conflict with a subdir from an existing repo
        caught = False
        try:
            existing_urls = distributor.form_rel_url_lookup_table([repo_a, conflict_repo_a]) 
        except Exception, e:
            caught = True
        self.assertTrue(caught)


    def test_basic_repo_publish_rel_path_conflict(self):
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "test_basic_repo_publish_rel_path_conflict"
        num_units = 10
        relative_url = "rel_a/rel_b/rel_a/"
        config = distributor_mocks.get_basic_config(https_publish_dir=self.https_publish_dir, 
                relative_url=relative_url, http=False, https=True)

        url_a = relative_url
        config_a = PluginCallConfiguration({"relative_url":url_a}, {})
        repo_a = RelatedRepository("repo_a_id", [config_a])

        # Simple check of direct conflict of a duplicate
        related_repos = [repo_a]
        distributor = YumDistributor()
        distributor.process_repo_auth_certificate_bundle = mock.Mock()
        status, msg = distributor.validate_config(repo, config, related_repos)
        self.assertFalse(status)
        expected_msg = "Relative url '%s' conflicts with existing relative_url of '%s' from repo '%s'" % (relative_url, url_a, repo_a.id)
        self.assertEqual(expected_msg, msg)

        # Check conflict with a subdir
        url_b = "rel_a/rel_b/"
        config_b = PluginCallConfiguration({"relative_url":url_b}, {})
        repo_b = RelatedRepository("repo_b_id", [config_b])
        related_repos = [repo_b]
        distributor = YumDistributor()
        distributor.process_repo_auth_certificate_bundle = mock.Mock()
        status, msg = distributor.validate_config(repo, config, related_repos)
        self.assertFalse(status)
        expected_msg = "Relative url '%s' conflicts with existing relative_url of '%s' from repo '%s'" % (relative_url, url_b, repo_b.id)
        self.assertEqual(expected_msg, msg)

        # Check no conflict with a pieces of a common subdir
        url_c = "rel_a/rel_b/rel_c"
        config_c = PluginCallConfiguration({"relative_url":url_c}, {})
        repo_c = RelatedRepository("repo_c_id", [config_c])

        url_d = "rel_a/rel_b/rel_d"
        config_d = PluginCallConfiguration({"relative_url":url_d}, {})
        repo_d = RelatedRepository("repo_d_id", [config_d])

        url_e = "rel_a/rel_b/rel_e/rel_e"
        config_e = PluginCallConfiguration({"relative_url":url_e}, {})
        repo_e = RelatedRepository("repo_e_id", [config_e])

        # Add a repo with no relative_url
        config_f = PluginCallConfiguration({"relative_url":None}, {})
        repo_f = RelatedRepository("repo_f_id", [config_f])

        related_repos = [repo_c, repo_d, repo_e, repo_f]
        distributor = YumDistributor()
        distributor.process_repo_auth_certificate_bundle = mock.Mock()

        status, msg = distributor.validate_config(repo, config, related_repos)
        self.assertTrue(status)
        self.assertEqual(msg, None)

        # Test with 2 repos and no relative_url
        config_h = PluginCallConfiguration({}, {})
        repo_h = RelatedRepository("repo_h_id", [config_h])

        config_i = PluginCallConfiguration({}, {})
        repo_i = RelatedRepository("repo_i_id", [config_i])

        status, msg = distributor.validate_config(repo_i, config, [repo_h])
        self.assertTrue(status)
        self.assertEqual(msg, None)

        # TODO:  Test, repo_1 has no rel url, so repo_1_id is used
        # Then 2nd repo is configured with rel_url of repo_1_id
        #  should result in a conflict



        # Ensure this test can handle a large number of repos
        test_repos = []
        for index in range(0,10000):
            test_url = "rel_a/rel_b/rel_e/repo_%s" % (index)
            test_config = PluginCallConfiguration({"relative_url":test_url}, {})
            r = RelatedRepository("repo_%s_id" % (index), [test_config])
            test_repos.append(r)
        related_repos = test_repos
        distributor = YumDistributor()
        distributor.process_repo_auth_certificate_bundle = mock.Mock()
        status, msg = distributor.validate_config(repo, config, related_repos)
        self.assertTrue(status)
        self.assertEqual(msg, None)

    def test_publish_progress(self):
        global progress_status
        progress_status = None

        def set_progress(progress):
            global progress_status
            progress_status = progress
        PROGRESS_FIELDS = ["num_success", "num_error", "items_left", "items_total", "error_details"]
        publish_conduit = distributor_mocks.get_publish_conduit(pkg_dir=self.pkg_dir)
        config = distributor_mocks.get_basic_config(https_publish_dir=self.https_publish_dir, http_publish_dir=self.http_publish_dir,
                relative_url="rel_temp/",
            generate_metadata=True, http=True, https=False)
        distributor = YumDistributor()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "test_progress_sync"
        publish_conduit.set_progress = mock.Mock()
        publish_conduit.set_progress.side_effect = set_progress
        distributor.publish_repo(repo, publish_conduit, config)

        self.assertTrue(progress_status is not None)
        self.assertTrue("packages" in progress_status)
        self.assertTrue(progress_status["packages"].has_key("state"))
        self.assertEqual(progress_status["packages"]["state"], "FINISHED")
        for field in PROGRESS_FIELDS:
            self.assertTrue(field in progress_status["packages"])

        self.assertTrue("distribution" in progress_status)
        self.assertTrue(progress_status["distribution"].has_key("state"))
        self.assertEqual(progress_status["distribution"]["state"], "FINISHED")
        for field in PROGRESS_FIELDS:
            self.assertTrue(field in progress_status["distribution"])

        self.assertTrue("metadata" in progress_status)
        self.assertTrue(progress_status["metadata"].has_key("state"))
        self.assertEqual(progress_status["metadata"]["state"], "FINISHED")

        self.assertTrue("publish_http" in progress_status)
        self.assertEqual(progress_status["publish_http"]["state"], "FINISHED")
        self.assertTrue("publish_https" in progress_status)
        self.assertEqual(progress_status["publish_https"]["state"], "SKIPPED")


    def test_remove_symlink(self):

        pub_dir = self.http_publish_dir
        link_path = os.path.join(pub_dir, "a", "b", "c", "d", "e")
        os.makedirs(link_path)
        link_path = os.path.join(link_path, "temp_link").rstrip('/')
        os.symlink(self.https_publish_dir, link_path)
        self.assertTrue(os.path.exists(link_path))

        distributor = YumDistributor()
        distributor.remove_symlink(pub_dir, link_path)
        self.assertFalse(os.path.exists(link_path))
        self.assertEqual(len(os.listdir(pub_dir)), 0)

    def test_consumer_payload(self):
        PAYLOAD_FIELDS = [ 'server_name', 'relative_path',
                          'protocols', 'gpg_keys', 'client_cert', 'ca_cert']
        http = True
        https = True
        relative_url = "/pub/content/"
        gpgkey = ["test_gpg_key",]
        auth_cert = open(os.path.join(self.data_dir, "cert.crt")).read()
        auth_ca = open(os.path.join(self.data_dir, "ca.key")).read()
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https, auth_cert=auth_cert, auth_ca=auth_ca, gpgkey=gpgkey)
        distributor = YumDistributor()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "test_payload"
        payload = distributor.create_consumer_payload(repo, config)
        for field in PAYLOAD_FIELDS:
            print field
            self.assertTrue(field in payload)

        self.assertTrue('http' in payload['protocols'])
        self.assertTrue('https' in payload['protocols'])
        print payload


    def test_cancel_publish(self):
        global updated_progress
        updated_progress = None

        def set_progress(progress):
            global updated_progress
            updated_progress = progress

        class TestPublishThread(threading.Thread):
            def __init__(self, working_dir, pkg_dir, config):
                threading.Thread.__init__(self)
                self.repo = mock.Mock(spec=Repository)
                self.repo.working_dir = working_dir
                self.repo.id = "test_cancel_publish"
                self.publish_conduit = distributor_mocks.get_publish_conduit(pkg_dir=pkg_dir)
                self.publish_conduit.set_progress = mock.Mock()
                self.publish_conduit.set_progress.side_effect = set_progress
                self.config = config
                self.distributor = YumDistributor()

            def run(self):
                self.distributor.publish_repo(self.repo, self.publish_conduit, self.config)

            def cancel(self):
                return self.distributor.cancel_publish_repo(self.repo)

        working_dir = os.path.join(self.temp_dir, "test_cancel_publish")

        try:
            ####
            # Prepare a directory with test data so that createrepo will run for a minute or more
            # this allows us time to interrupt it and test that cancel is working
            ####
            num_links = 1500
            source_rpm = os.path.join(self.data_dir, "createrepo_test", "pulp-large_1mb_test-packageA-0.1.1-1.fc14.noarch.rpm")
            self.assertTrue(os.path.exists(source_rpm))
            os.makedirs(working_dir)
            for index in range(num_links):
                temp_name = "temp_link-%s.rpm" % (index)
                temp_name = os.path.join(working_dir, temp_name)
                if not os.path.exists(temp_name):
                    os.symlink(source_rpm, temp_name)
    
            config = distributor_mocks.get_basic_config(https_publish_dir=self.https_publish_dir, 
                http_publish_dir=self.http_publish_dir, relative_url="rel_temp/",
                generate_metadata=True, http=True, https=False)
            test_thread = TestPublishThread(working_dir, self.pkg_dir, config)
            test_thread.start()
            running = False
            for index in range(15):
                if updated_progress and updated_progress.has_key("metadata") and updated_progress["metadata"].has_key("state"):
                    if updated_progress["metadata"]["state"] in ["IN_PROGRESS", "FAILED", "FINISHED", "CANCELED"]:
                        running = True
                        break
                time.sleep(1)
            self.assertTrue(running)
            self.assertEquals(updated_progress["metadata"]["state"], "IN_PROGRESS")
            self.assertTrue(test_thread.cancel())
            for index in range(15):
                if updated_progress and updated_progress.has_key("metadata") and updated_progress["metadata"].has_key("state"):
                    if updated_progress["metadata"]["state"] in ["FAILED", "FINISHED", "CANCELED"]:
                        break
                time.sleep(1)
            self.assertEquals(updated_progress["metadata"]["state"], "CANCELED")
        finally:
            if os.path.exists(working_dir):
                shutil.rmtree(working_dir)
