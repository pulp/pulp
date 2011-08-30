#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
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

# Python
import logging
import sys
import os
import time
import unittest
import shutil
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil
from pulp.server.exporter.plugins.package import PackageExporter
from pulp.server.exporter.plugins.packagegroup import CompsExporter
from pulp.server.exporter.plugins.distribution import DistributionExporter
from pulp.server.exporter.plugins.errata import ErrataExporter
from pulp.server.exporter.plugins.other import OtherExporter
from pulp.server.api import repo_sync
from pulp.server.tasking import task
from pulp.server import async, constants, util
logging.root.setLevel(logging.ERROR)
qpid = logging.getLogger('qpid.messaging')
qpid.setLevel(logging.ERROR)

class TestExporterApi(testutil.PulpAsyncTest):

    def clean(self):
        testutil.PulpAsyncTest.clean(self)
        shutil.rmtree(constants.LOCAL_STORAGE, ignore_errors=True)
        pass
    
    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        my_dir = os.path.abspath(os.path.dirname(__file__))
        datadir = my_dir + "/data/repo_for_export/"
        repo_url = "file://%s" % datadir
        repo_1 = self.repo_api.create('test_export_repo', 'some name', \
            'i386', 'file://%s' % repo_url)
        self._perform_sync(repo_1)
        self.found_1 = self.repo_api.repository('test_export_repo')

    def test_repo_exporter(self):
        # test package export
        packages_1 = self.found_1['packages']
        pe = PackageExporter('test_export_repo', target_dir='/tmp/pulp/myexport/')
        pe.export()
        repo_2 = self.repo_api.create('test_import_repo_package', 'some name', \
            'i386', 'file:///tmp/pulp/myexport/')
        self._perform_sync(repo_2)
        found_2 = self.repo_api.repository('test_import_repo_package')
        packages_2 = found_2['packages']
        self.assertEquals(len(packages_1), len(packages_2))
        print "CCCCCCCCCC %s %s" % (packages_2, packages_1)

        # test errata export
        errata_1  = self.found_1['errata']
        ee = ErrataExporter('test_export_repo', target_dir='/tmp/pulp/myexport/')
        ee.export()
        repo_3 = self.repo_api.create('test_import_repo_errata', 'some name', \
            'i386', 'file:///tmp/pulp/myexport/')
        self._perform_sync(repo_3)
        found_3 = self.repo_api.repository('test_import_repo_errata')
        errata_3 = found_3['errata']
        self.assertEquals(len(errata_1), len(errata_3))
        print "CCCCCCCCCC %s %s" % (errata_1, errata_3)

        # test distribution export
        distribution_1 = self.found_1['distributionid']
        de = DistributionExporter('test_export_repo', target_dir='/tmp/pulp/myexport/')
        de.export()
        repo_4 = self.repo_api.create('test_import_repo_distro', 'some name', \
            'i386', 'file:///tmp/pulp/myexport/')
        self._perform_sync(repo_4)
        found_4 = self.repo_api.repository('test_import_repo_distro')
        distribution_2 = found_4['distributionid']
        self.assertEquals(len(distribution_1), len(distribution_2))

        # test other exports
        tgt_dir = '/tmp/pulp/myexport/'
        oe = OtherExporter('test_export_repo', target_dir=tgt_dir)
        oe.export()
        repomd_path = os.path.join(tgt_dir, 'repodata/repomd.xml')
        print "GGGGGGGGGGGGGg",repomd_path, os.path.exists(repomd_path)
        assert(os.path.exists(repomd_path))
        ftypes = util.get_repomd_filetypes(repomd_path)
        assert('product' in ftypes)

        # test package group export
        packagegroup_1 = self.found_1['packagegroups']
        ce = CompsExporter('test_export_repo', target_dir='/tmp/pulp/myexport/')
        ce.export()
        repo_5 = self.repo_api.create('test_import_repo_pg', 'some name', \
            'i386', 'file:///tmp/pulp/myexport/')
        self._perform_sync(repo_5)
        found_5 = self.repo_api.repository('test_import_repo_pg')
        packagegroup_2 = found_5['packagegroups']
        #assert(len(packagegroup_1) == len(packagegroup_2))
        
    def _perform_sync(self, r):
        sync_tasks = []
        t = repo_sync.sync(r["id"])
        sync_tasks.append(t)
        # Poll tasks and wait for sync to finish
        waiting_tasks = [t.id for t in sync_tasks]
        while len(waiting_tasks) > 0:
            time.sleep(1)
            for t_id in waiting_tasks:
                found_tasks = async.find_async(id=t_id)
                self.assertEquals(len(found_tasks), 1)
                updated_task = found_tasks[0]
                if updated_task.state in task.task_complete_states:
                    self.assertEquals(updated_task.state, task.task_finished)
                    waiting_tasks.remove(t_id)

if __name__ == '__main__':
    unittest.main()
