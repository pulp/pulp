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
import traceback
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/importers/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/distributors/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../common")

from yum_distributor import metadata

from pulp.plugins.model import Repository

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../yum_importer")
import distributor_mocks

class TestMetadata(unittest.TestCase):

    def setUp(self):
        super(TestMetadata, self).setUp()
        self.init()

    def tearDown(self):
        super(TestMetadata, self).tearDown()
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data"))
        self.repodata_dir = os.path.join(self.data_dir, "test_repo_metadata/repodata/")

    def clean(self):
        shutil.rmtree(self.temp_dir)
        if os.path.exists(self.repodata_dir):
            shutil.rmtree(self.repodata_dir)

    def test_generate_metadata(self):
        mock_repo = mock.Mock(spec=Repository)
        mock_repo.id = "test_repo"
        mock_repo.scratchpad = {"checksum_type" : "sha"}
        mock_repo.working_dir = os.path.join(self.data_dir, "test_repo_metadata")
        # Confirm required and optional are successful
        optional_kwargs = {"generate_metadata" :  1}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        mock_publish_conduit = distributor_mocks.get_publish_conduit()
        status, errors = metadata.generate_metadata(mock_repo, mock_publish_conduit, config)
        self.assertEquals(status, True)
        optional_kwargs = {"generate_metadata" :  0}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        mock_publish_conduit = distributor_mocks.get_publish_conduit()
        status, errors = metadata.generate_metadata(mock_repo, mock_publish_conduit, config)
        self.assertEquals(status, False)

    def test_get_checksum_type(self):
        mock_repo = mock.Mock(spec=Repository)
        mock_repo.id = "test_repo"
        mock_repo.working_dir = os.path.join(self.data_dir, "pulp_unittest")
        optional_kwargs = {"checksum_type" :  "sha512"}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        mock_publish_conduit = distributor_mocks.get_publish_conduit()
        _checksum_type_value = metadata.get_repo_checksum_type(mock_repo, mock_publish_conduit, config)
        print _checksum_type_value
        self.assertEquals(_checksum_type_value, optional_kwargs['checksum_type'])
        optional_kwargs = {}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        _checksum_type_value = metadata.get_repo_checksum_type(mock_repo, mock_publish_conduit, config)
        print _checksum_type_value
        self.assertEquals(_checksum_type_value, "sha")
        mock_repo.scratchpad = None
        optional_kwargs = {}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        mock_publish_conduit = distributor_mocks.get_publish_conduit(checksum_type=None)
        _checksum_type_value = metadata.get_repo_checksum_type(mock_repo, mock_publish_conduit, config)
        print _checksum_type_value
        self.assertEquals(_checksum_type_value, "sha256")

    def test_cancel_metadata_generation(self):
        global updated_progress
        updated_progress = None

        def set_progress(type_id, progress):
            global updated_progress
            updated_progress = progress
            print "updated_progress:  %s" % (updated_progress)

        class TestGenerateThread(threading.Thread):
            def __init__(self, working_dir):
                threading.Thread.__init__(self)
                self.mock_repo = mock.Mock(spec=Repository)
                self.mock_repo.id = "test_cancel_metadata_generation"
                self.mock_repo.scratchpad = {"checksum_type" : "sha"}
                self.mock_repo.working_dir = working_dir
                optional_kwargs = {"generate_metadata" :  1}
                self.config = distributor_mocks.get_basic_config(**optional_kwargs)
                self.mock_publish_conduit = distributor_mocks.get_publish_conduit()
                self.mock_publish_conduit.set_progress = mock.Mock()
                self.mock_publish_conduit.set_progress.side_effect = set_progress
                self.status = None
                self.errors = None
                self.finished = False

            def run(self):
                self.status, self.errors = metadata.generate_metadata(self.mock_repo, self.mock_publish_conduit, self.config, set_progress)
                self.finished = True
            
            def __check_pid(self, pid):
                try:
                    os.kill(pid, 0)
                    return True
                except OSError:
                    return False

            def is_running(self):
                pid = metadata.get_createrepo_pid(self.mock_repo.working_dir)
                if not pid:
                    print "Unable to find a pid for createrepo on %s" % (self.mock_repo.working_dir)
                    return False
                if self.__check_pid(pid):
                    return True
                else:
                    print "PID found: %s, for %s, but it is not running" % (pid, self.mock_repo.working_dir)
                    return false

            def cancel(self):
                return metadata.cancel_createrepo(self.mock_repo.working_dir)
        try:
            ####
            # Prepare a directory with test data so that createrepo will run for a minute or more
            # this allows us time to interrupt it and test that cancel is working
            ####
            num_links = 1500
            source_rpm = os.path.join(self.data_dir, "createrepo_test", "pulp-large_1mb_test-packageA-0.1.1-1.fc14.noarch.rpm")
            self.assertTrue(os.path.exists(source_rpm))
            working_dir = os.path.join(self.temp_dir, "test_cancel_metadata_generation")
            os.makedirs(working_dir)
            self.assertTrue(os.path.exists(working_dir))

            for index in range(num_links):
                temp_name = "temp_link-%s.rpm" % (index)
                temp_name = os.path.join(working_dir, temp_name)
                if not os.path.exists(temp_name):
                    os.symlink(source_rpm, temp_name)
                self.assertTrue(os.path.exists(temp_name))
            ###
            # Kick off createrepo
            ###
            test_thread = TestGenerateThread(working_dir)
            test_thread.start()
            ###
            # Wait till we get a response from progress that createrepo is running
            ###
            running = False
            for index in range(15):
                if updated_progress and updated_progress.has_key("state"):
                    if updated_progress["state"] in ["FAILED", "FINISHED", "IN_PROGRESS", "CANCELED"]:
                        running = True
                        break
                time.sleep(1)
            self.assertTrue(running)
            self.assertEquals(updated_progress["state"], "IN_PROGRESS")
            for index in range(15):
                # Check that the createrepo process has been executed and is running
                if test_thread.is_running():
                    break
                time.sleep(1)
            self.assertTrue(test_thread.cancel())
            for index in range(15):
                if updated_progress and updated_progress.has_key("state"):
                    if updated_progress["state"] in ["FAILED", "FINISHED", "CANCELED"]:
                        break
                time.sleep(1)
            self.assertEquals(updated_progress["state"], "CANCELED")
        finally:
            for index in range(15):
                if test_thread.finished:
                    break
                time.sleep(1)
            if os.path.exists(working_dir):
                try:
                    shutil.rmtree(working_dir)
                except Exception, e:
                    # Note:  We are seeing intermittent errors from this rmtree
                    #        yet, this directory is subsequently delete with no errors when self.clean()
                    #        runs and deletes self.temp_dir
                    print "Caught exception from trying to cleanup: %s" % (working_dir)
                    traceback.print_exc()


