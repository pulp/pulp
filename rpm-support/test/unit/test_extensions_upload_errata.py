# Copyright (c 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2 or (at your option any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os

import mock
from pulp.client.commands.repo.upload import UploadCommand, FLAG_VERBOSE
from pulp.client.commands.options import OPTION_REPO_ID

from pulp_rpm.common.ids import TYPE_ID_ERRATA
from pulp_rpm.extension.admin.upload import errata
import rpm_support_base


DATA_DIR = os.path.abspath(os.path.dirname(__file__)) + '/data/test_extensions_upload_errata'


class CreateRpmCommandTests(rpm_support_base.PulpClientTests):

    def setUp(self):
        super(CreateRpmCommandTests, self).setUp()
        self.upload_manager = mock.MagicMock()
        self.command = errata.CreateErratumCommand(self.context, self.upload_manager)

    def test_structure(self):
        self.assertTrue(isinstance(self.command, UploadCommand))
        self.assertEqual(self.command.name, errata.NAME)
        self.assertEqual(self.command.description, errata.DESC)

        expected_options = set([errata.OPT_ERRATUM_ID, errata.OPT_TITLE, errata.OPT_DESC,
                            errata.OPT_VERSION, errata.OPT_RELEASE, errata.OPT_TYPE,
                            errata.OPT_STATUS, errata.OPT_UPDATED, errata.OPT_ISSUED,
                            errata.OPT_REFERENCE, errata.OPT_PKG_LIST, errata.OPT_FROM,
                            errata.OPT_PUSHCOUNT, errata.OPT_REBOOT, errata.OPT_SEVERITY,
                            errata.OPT_RIGHTS, errata.OPT_SUMMARY, errata.OPT_SOLUTION,
                            FLAG_VERBOSE, OPTION_REPO_ID])
        found_options = set(self.command.options)

        self.assertEqual(expected_options, found_options)

    def test_determine_type_id(self):
        type_id = self.command.determine_type_id(None)
        self.assertEqual(type_id, TYPE_ID_ERRATA)

    def test_generate_unit_key(self):
        args = {errata.OPT_ERRATUM_ID.keyword : 'test-erratum'}
        unit_key = self.command.generate_unit_key(None, **args)

        self.assertEqual(unit_key['id'], 'test-erratum')

    def test_generate_metadata(self):
        # Setup
        pkg_list_file = os.path.join(DATA_DIR, 'packages.csv')
        ref_list_file = os.path.join(DATA_DIR, 'references.csv')
        args = {
            errata.OPT_PKG_LIST.keyword : pkg_list_file,
            errata.OPT_REFERENCE.keyword : ref_list_file,
            errata.OPT_TITLE.keyword : 'test-title',
            errata.OPT_DESC.keyword : 'test-description',
            errata.OPT_VERSION.keyword : 'test-version',
            errata.OPT_RELEASE.keyword : 'test-release',
            errata.OPT_TYPE.keyword : 'test-type',
            errata.OPT_STATUS.keyword : 'test-status',
            errata.OPT_UPDATED.keyword : 'test-updated',
            errata.OPT_ISSUED.keyword : 'test-issued',
            errata.OPT_SEVERITY.keyword : 'test-severity',
            errata.OPT_RIGHTS.keyword : 'test-rights',
            errata.OPT_SUMMARY.keyword : 'test-summary',
            errata.OPT_SOLUTION.keyword : 'test-solution',
            errata.OPT_FROM.keyword : 'test-from',
            errata.OPT_REBOOT.keyword : 'test-reboot',
            errata.OPT_PUSHCOUNT.keyword : '1',
        }

        # Test
        metadata = self.command.generate_metadata(None, **args)

        # Verify
        expected_package_list = self.command.parse_package_csv(pkg_list_file, 'test-release')
        expected_reference_list = self.command.parse_reference_csv(ref_list_file)
        expected = {
            'title' : 'test-title',
            'description' : 'test-description',
            'version' : 'test-version',
            'release' : 'test-release',
            'type' : 'test-type',
            'status' : 'test-status',
            'updated' : 'test-updated',
            'issued' : 'test-issued',
            'severity' : 'test-severity',
            'rights' : 'test-rights',
            'summary' : 'test-summary',
            'solution' : 'test-solution',
            'from_str' : 'test-from',
            'pushcount' : 1,
            'reboot_suggested' : 'test-reboot',
            'pkglist' : expected_package_list,
            'references' : expected_reference_list,
        }
        self.assertEqual(expected, metadata)

