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
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/distributors/")

from yum_distributor.distributor import YumDistributor
from pulp.plugins.model import Repository
from pulp_rpm.repo_auth.repo_cert_utils import M2CRYPTO_HAS_CRL_SUPPORT

import distributor_mocks
import mock
import rpm_support_base
import unittest

class TestValidateConfig(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestValidateConfig, self).setUp()
        self.repo = mock.Mock(spec=Repository)
        self.repo.id = "testrepo"
        self.distributor = YumDistributor()
        self.distributor.process_repo_auth_certificate_bundle = mock.Mock()
        self.init()

    def tearDown(self):
        super(TestValidateConfig, self).tearDown()

    def init(self):
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "./data"))

    def test_config_relative_path(self):

        http = True
        https = False
        relative_url = 123
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertFalse(state)

        relative_url = "test_path"
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_http(self):

        http = "true"
        https = False
        relative_url = "test_path"
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertFalse(state)

        http = True
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_https(self):

        http = True
        https = "False"
        relative_url = "test_path"
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertFalse(state)

        https = True
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_protected(self):
        http = True
        https = False
        relative_url = "test_path"
        protected = "false"
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https, protected=protected)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertFalse(state)

        protected = True
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https, protected=protected)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_generate_metadata(self):
        http = True
        https = False
        relative_url = "test_path"
        generate_metadata = "false"
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https,
            generate_metadata=generate_metadata)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertFalse(state)

        generate_metadata = True
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https,
            generate_metadata=generate_metadata)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_checksum_type(self):
        http = True
        https = False
        relative_url = "test_path"
        checksum_type = "fake"
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https,
            checksum_type=checksum_type)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertFalse(state)

        checksum_type = "sha"
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https,
            checksum_type=checksum_type)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_skip_content_types(self):
        http = True
        https = False
        relative_url = "test_path"
        skip_content_types = "fake"
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https,
            skip=skip_content_types)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertFalse(state)

        skip_content_types = []
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https,
            skip=skip_content_types)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_auth_pem(self):
        if not M2CRYPTO_HAS_CRL_SUPPORT:
            return
        http = True
        https = False
        relative_url = "test_path"
        auth_cert = "fake"
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https,
            auth_cert=auth_cert)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertFalse(state)

        auth_cert = open(os.path.join(self.data_dir, "cert.crt")).read()
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https,
            auth_cert=auth_cert)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertTrue(state)

    def test_config_auth_ca(self):
        if not M2CRYPTO_HAS_CRL_SUPPORT:
            return
        http = True
        https = False
        relative_url = "test_path"
        auth_ca = "fake"
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https,
            auth_ca=auth_ca)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertFalse(state)

        auth_ca = open(os.path.join(self.data_dir, "valid_ca.crt")).read()
        config = distributor_mocks.get_basic_config(relative_url=relative_url, http=http, https=https,
            auth_ca=auth_ca)
        state, msg = self.distributor.validate_config(self.repo, config, [])
        self.assertTrue(state)


