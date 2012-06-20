# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")

from yum_importer.importer import YumImporter
import importer_mocks
from pulp.plugins.model import Repository
from pulp_rpm.repo_auth.repo_cert_utils import M2CRYPTO_HAS_CRL_SUPPORT

import rpm_support_base

class TestValidateConfig(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestValidateConfig, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.repo = mock.Mock(spec=Repository)
        self.repo.working_dir = os.path.join(self.temp_dir, "repo_working_dir")
        os.makedirs(self.repo.working_dir)
        self.importer = YumImporter()
        self.init()

    def tearDown(self):
        super(TestValidateConfig, self).tearDown()
        shutil.rmtree(self.temp_dir)

    def init(self):
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data"))

    def test_config_feed_url(self):

        # test bad feed_url
        feed_url = "fake://example.redhat.com/"
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        feed_url = "http://example.redhat.com/"
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_ssl_verify(self):
        feed_url = "http://example.redhat.com/"
        ssl_verify = "fake"
        config = importer_mocks.get_basic_config(feed_url=feed_url, ssl_verify=ssl_verify)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        ssl_verify = True
        config = importer_mocks.get_basic_config(feed_url=feed_url, ssl_verify=ssl_verify)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)


    def test_config_ssl_ca_cert(self):
        if not M2CRYPTO_HAS_CRL_SUPPORT:
            return
        feed_url = "http://example.redhat.com/"
        ssl_ca_cert = "fake_path_to_ca"
        config = importer_mocks.get_basic_config(feed_url=feed_url, ssl_ca_cert=ssl_ca_cert)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        ssl_ca_cert = open(os.path.join(self.data_dir, "valid_ca.crt")).read()
        config = importer_mocks.get_basic_config(feed_url=feed_url, ssl_ca_cert=ssl_ca_cert)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

        ssl_ca_cert_filename = os.path.join(self.repo.working_dir, "ssl_ca_cert")
        self.assertTrue(os.path.exists(ssl_ca_cert_filename))
        ca_cert_data = open(ssl_ca_cert_filename).read()
        self.assertEqual(ca_cert_data, ssl_ca_cert)

    def test_config_ssl_client_cert(self):
        if not M2CRYPTO_HAS_CRL_SUPPORT:
            return
        feed_url = "http://example.redhat.com/"
        ssl_client_cert = "fake_path_to_client_cert"
        config = importer_mocks.get_basic_config(feed_url=feed_url, ssl_client_cert=ssl_client_cert)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        ssl_client_cert = open(os.path.join(self.data_dir, "cert.crt")).read()
        config = importer_mocks.get_basic_config(feed_url=feed_url, ssl_client_cert=ssl_client_cert)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)
        
        ssl_client_cert_filename = os.path.join(self.repo.working_dir, "ssl_client_cert")
        self.assertTrue(os.path.exists(ssl_client_cert_filename))
        client_cert_data = open(ssl_client_cert_filename).read()
        self.assertEqual(client_cert_data, ssl_client_cert)

    def test_config_proxy_url(self):
        feed_url = "http://example.redhat.com/"
        proxy_url = "fake://proxy"
        config = importer_mocks.get_basic_config(feed_url=feed_url, proxy_url=proxy_url)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        proxy_url = "http://proxy"
        config = importer_mocks.get_basic_config(feed_url=feed_url, proxy_url=proxy_url)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_max_speed(self):
        feed_url = "http://example.redhat.com/"
        max_speed = "fake_speed"
        config = importer_mocks.get_basic_config(feed_url=feed_url, max_speed=max_speed)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        max_speed = 100
        config = importer_mocks.get_basic_config(feed_url=feed_url, max_speed=max_speed)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_verify_checksum(self):
        feed_url = "http://example.redhat.com/"
        verify_checksum = "fake_bool"
        config = importer_mocks.get_basic_config(feed_url=feed_url, verify_checksum=verify_checksum)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        verify_checksum = True
        config = importer_mocks.get_basic_config(feed_url=feed_url, verify_checksum=verify_checksum)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_verify_size(self):
        feed_url = "http://example.redhat.com/"
        verify_size = "fake_bool"
        config = importer_mocks.get_basic_config(feed_url=feed_url, verify_size=verify_size)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        verify_size = True
        config = importer_mocks.get_basic_config(feed_url=feed_url, verify_size=verify_size)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_newest(self):
        feed_url = "http://example.redhat.com/"
        newest = "fake_bool"
        config = importer_mocks.get_basic_config(feed_url=feed_url, newest=newest)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        newest = True
        config = importer_mocks.get_basic_config(feed_url=feed_url, newest=newest)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_remove_old(self):
        feed_url = "http://example.redhat.com/"
        remove_old  = "fake_bool"
        config = importer_mocks.get_basic_config(feed_url=feed_url, remove_old=remove_old)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        remove_old  = True
        config = importer_mocks.get_basic_config(feed_url=feed_url, remove_old=remove_old)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_num_threads(self):
        feed_url = "http://example.redhat.com/"
        num_threads = "fake_int"
        config = importer_mocks.get_basic_config(feed_url=feed_url, num_threads=num_threads)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        num_threads = 5
        config = importer_mocks.get_basic_config(feed_url=feed_url, num_threads=num_threads)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_num_old_packages(self):
        feed_url = "http://example.redhat.com/"
        num_old_packages = "fake_int"
        config = importer_mocks.get_basic_config(feed_url=feed_url, num_old_packages=num_old_packages)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        num_old_packages = 4
        config = importer_mocks.get_basic_config(feed_url=feed_url, num_old_packages=num_old_packages)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_purge_orphaned(self):
        feed_url = "http://example.redhat.com/"
        purge_orphaned = "fake_bool"
        config = importer_mocks.get_basic_config(feed_url=feed_url, purge_orphaned=purge_orphaned)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        purge_orphaned = True
        config = importer_mocks.get_basic_config(feed_url=feed_url, purge_orphaned=purge_orphaned)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_checksum_type(self):
        feed_url = "http://example.redhat.com/"
        checksum_type ="fake_checksum"
        config = importer_mocks.get_basic_config(feed_url=feed_url, checksum_type=checksum_type)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        checksum_type ="sha"
        config = importer_mocks.get_basic_config(feed_url=feed_url, checksum_type=checksum_type)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_skip(self):
        feed_url = "http://example.redhat.com/"
        skip_content_types = ""
        config = importer_mocks.get_basic_config(feed_url=feed_url, skip=skip_content_types)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertFalse(state)

        skip_content_types = []
        config = importer_mocks.get_basic_config(feed_url=feed_url, skip=skip_content_types)
        state, msg = self.importer.validate_config(self.repo, config, [])
        self.assertTrue(state)
