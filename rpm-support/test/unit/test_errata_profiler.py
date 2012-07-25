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

import mock
import os
import random
import shutil
import sys
import tempfile
import unittest
import yum
from pulp.plugins.model import Consumer, Repository, Unit
from pulp.server.managers import factory
from pulp.server.managers.consumer.cud import ConsumerManager
from pulp_rpm.yum_plugin import comps_util, util, updateinfo

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/profilers/")
import profiler_mocks
import rpm_support_base
from rpm_errata_profiler.profiler import RPMErrataProfiler, PROFILER_TYPE_ID, ERRATA_TYPE_ID, RPM_TYPE_ID, RPM_UNIT_KEY

class TestErrataProfiler(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestErrataProfiler, self).setUp()
        self.data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        self.updateinfo_xml_path = os.path.join(self.data_dir, "test_errata_local_sync", "updateinfo.xml.gz")
        self.consumer_id = "test_errata_profiler_consumer_id"
        self.profiles = self.get_test_profile()
        self.test_consumer = Consumer(self.consumer_id, self.profiles)

    def tearDown(self):
        super(TestErrataProfiler, self).tearDown()
        shutil.rmtree(self.temp_dir)

    def create_rpm_unit(self, name, epoch, version, release, arch, checksum, 
            checksumtype, metadata=None):
        unit_key = {"name":name, "epoch":epoch, "version":version, "release":release, 
                "arch":arch, "checksum":checksum, "checksumtype":checksumtype}
        if not metadata:
            metadata = {"dummy_values":"values"}
        return Unit(RPM_TYPE_ID, unit_key, metadata, None)

    def create_profile_entry(self, name, epoch, version, release, arch, vendor):
        return {"name":name, "epoch": epoch, "version":version, "release":release, 
                "arch":arch, "vendor":vendor}
        
    def get_test_rpm_units(self):
        rpm_units = []
        u = self.create_rpm_unit("emoticons", '0', "0.1", "2", "x86_64", "366bb5e73a5905eacb82c96e0578f92b", "md5")
        rpm_units.append(u)
        u = self.create_rpm_unit("patb", '0', "0.1", "2", "x86_64", "f3c197a29d9b66c5b65c5d62b25db5b4", "md5")
        rpm_units.append(u)
        return rpm_units

    def get_test_errata_object(self):
        errata_from_xml = updateinfo.get_errata(self.updateinfo_xml_path)
        self.assertTrue(len(errata_from_xml) > 0)
        return errata_from_xml[0]

    def get_test_profile(self):
        foo = self.create_profile_entry("emoticons", 0, "0.0.1", "1", "x86_64", "Test Vendor")
        bar = self.create_profile_entry("patb", 0, "0.0.1", "1", "x86_64", "Test Vendor")
        return {RPM_TYPE_ID:[foo, bar]}

    def test_metadata(self):
        data = RPMErrataProfiler.metadata()
        self.assertTrue(data.has_key("id"))
        self.assertEquals(data['id'], PROFILER_TYPE_ID)
        self.assertTrue(data.has_key("display_name"))
        self.assertTrue(data.has_key("types"))
        self.assertTrue(ERRATA_TYPE_ID in data["types"])

    def test_get_rpms_from_errata(self):
        errata_obj = self.get_test_errata_object()
        errata_unit = Unit(ERRATA_TYPE_ID, {"id":errata_obj["id"]}, errata_obj, None)
        prof = RPMErrataProfiler()
        rpms = prof.get_rpms_from_errata(errata_unit)
        # Expected data:
        # [{'src': 'xen-3.0.3-80.el5_3.3.src.rpm', 'name': 'emoticons', 
        #   'sum': ('md5', '366bb5e73a5905eacb82c96e0578f92b'), 
        #   'filename': 'emoticons-0.1-2.x86_64.rpm', 'epoch': '0', 
        #   'version': '0.1', 'release': '2', 'arch': 'x86_64'}, 
        # {'src': 'xen-3.0.3-80.el5_3.3.src.rpm', 'name': 'patb', 
        #   'sum': ('md5', 'f3c197a29d9b66c5b65c5d62b25db5b4'), 
        #   'filename': 'patb-0.1-2.x86_64.rpm', 'epoch': '0', 
        #   'version': '0.1', 'release': '2', 'arch': 'x86_64'}]
        self.assertEqual(len(rpms), 2)
        self.assertTrue(rpms[0]["name"] in ['emoticons', 'patb'])
        self.assertTrue(rpms[1]["name"] in ['emoticons', 'patb'])
        for r in rpms:
            for key in ["name", "filename", "epoch", "version", "release"]:
                self.assertTrue(r.has_key(key))
                self.assertTrue(r[key])

    def test_find_unit_associated_to_consumer(self):
        test_repo = profiler_mocks.get_repo("test_repo_id")
        prof = RPMErrataProfiler()
        dummy_unit_key = "dummy_value"
        dummy_metadata = {"name":"value"}
        existing_units = [ Unit(RPM_TYPE_ID, dummy_unit_key, dummy_metadata, None) ]
        conduit = profiler_mocks.get_profiler_conduit(existing_units=existing_units, repo_bindings=[test_repo])
        found_rpm = prof.find_unit_associated_to_consumer(RPM_TYPE_ID, dummy_unit_key, self.test_consumer, conduit)
        self.assertTrue(found_rpm)
        self.assertTrue(found_rpm.type_id, RPM_TYPE_ID)
        self.assertTrue(found_rpm.unit_key, dummy_unit_key)
        self.assertTrue(found_rpm.metadata, dummy_metadata)

    def test_rpms_applicable_to_consumer(self):
        errata_rpms = []
        prof = RPMErrataProfiler()
        applicable_rpms, old_rpms = prof.rpms_applicable_to_consumer(Consumer("test", {}), errata_rpms)
        self.assertEqual(applicable_rpms, [])
        self.assertEqual(old_rpms, {})
        #
        # Get rpm dictionaries embedded in an errata
        #
        errata_obj = self.get_test_errata_object()
        errata_unit = Unit(ERRATA_TYPE_ID, {"id":errata_obj["id"]}, errata_obj, None)
        errata_rpms = prof.get_rpms_from_errata(errata_unit)
        # Test with 2 newer RPMs in the test errata
        #  The consumer has already been configured with a profile containing 'emoticons' and 'patb' rpms
        applicable_rpms, old_rpms = prof.rpms_applicable_to_consumer(self.test_consumer, errata_rpms)
        self.assertTrue(applicable_rpms)
        self.assertTrue(old_rpms)
        self.assertEqual(len(applicable_rpms), 2)
        self.assertTrue(old_rpms.has_key("emoticons.x86_64"))
        self.assertEqual("emoticons", old_rpms["emoticons.x86_64"]["installed"]["name"])
        self.assertEqual("0.0.1", old_rpms["emoticons.x86_64"]["installed"]["version"])

    def test_translate(self):
        # Setup test data
        errata_obj = self.get_test_errata_object()
        errata_unit = Unit(ERRATA_TYPE_ID, {"id":errata_obj["id"]}, errata_obj, None)
        expected_rpm_units = self.get_test_rpm_units()
        existing_units = [errata_unit]
        existing_units.extend(expected_rpm_units)
        test_repo = profiler_mocks.get_repo("test_repo_id")
        conduit = profiler_mocks.get_profiler_conduit(existing_units=existing_units, repo_bindings=[test_repo])
        example_errata = {"unit_key":errata_unit.unit_key, "type_id":ERRATA_TYPE_ID}
        # Test
        prof = RPMErrataProfiler()
        translated_rpm_units = prof.translate(example_errata, self.test_consumer, conduit)
        self.assertTrue(len(translated_rpm_units), len(expected_rpm_units))

    def test_unit_applicable(self):
        errata_obj = self.get_test_errata_object()
        errata_unit = Unit(ERRATA_TYPE_ID, {"id":errata_obj["id"]}, errata_obj, None)
        expected_rpm_units = self.get_test_rpm_units()
        existing_units = [errata_unit]
        existing_units.extend(expected_rpm_units)
        test_repo = profiler_mocks.get_repo("test_repo_id")
        conduit = profiler_mocks.get_profiler_conduit(existing_units=existing_units, repo_bindings=[test_repo])
        example_errata = {"unit_key":errata_unit.unit_key, "type_id":ERRATA_TYPE_ID}
        
        prof = RPMErrataProfiler()
        report = prof.unit_applicable(self.test_consumer, example_errata, None, conduit)
        self.assertTrue(report.applicable)
        self.assertEqual(report.unit, example_errata)
        self.assertEqual(len(report.summary["applicable_rpms"]), 2)
        self.assertEqual(len(report.details["rpms_to_upgrade"]), 2)

    def test_install_units(self):
        errata_obj = self.get_test_errata_object()
        errata_unit = Unit(ERRATA_TYPE_ID, {"id":errata_obj["id"]}, errata_obj, None)
        expected_rpm_units = self.get_test_rpm_units()
        existing_units = [errata_unit]
        existing_units.extend(expected_rpm_units)
        test_repo = profiler_mocks.get_repo("test_repo_id")
        conduit = profiler_mocks.get_profiler_conduit(existing_units=existing_units, repo_bindings=[test_repo])
        example_errata = {"unit_key":errata_unit.unit_key, "type_id":ERRATA_TYPE_ID}
        
        prof = RPMErrataProfiler()
        translated_units  = prof.install_units(self.test_consumer, [example_errata], None, None, conduit)
        self.assertEqual(len(translated_units), 2)

    def test_update_units(self):
        errata_obj = self.get_test_errata_object()
        errata_unit = Unit(ERRATA_TYPE_ID, {"id":errata_obj["id"]}, errata_obj, None)
        expected_rpm_units = self.get_test_rpm_units()
        existing_units = [errata_unit]
        existing_units.extend(expected_rpm_units)
        test_repo = profiler_mocks.get_repo("test_repo_id")
        conduit = profiler_mocks.get_profiler_conduit(existing_units=existing_units, repo_bindings=[test_repo])
        example_errata = {"unit_key":errata_unit.unit_key, "type_id":ERRATA_TYPE_ID}
        
        prof = RPMErrataProfiler()
        translated_units  = prof.update_units(self.test_consumer, [example_errata], None, None, conduit)
        self.assertEqual(len(translated_units), 2)




