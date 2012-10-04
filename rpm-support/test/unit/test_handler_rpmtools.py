# Copyright (c) 2010 Red Hat, Inc.
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

import mock_yum
from mock import Mock
from mock_yum import YumBase
from rpm_support_base import PulpRPMTests


class ToolTest(PulpRPMTests):

    def setUp(self):
        PulpRPMTests.setUp(self)
        mock_yum.install()
        from pulp_rpm.handler.rpmtools import Package, PackageGroup
        self.Package = Package
        self.PackageGroup = PackageGroup

    def tearDown(self):
        PulpRPMTests.tearDown(self)
        YumBase.reset()


class TestPackages(ToolTest):

    def verify(self, report, installed=[], updated=[], removed=[]):
        resolved = []
        deps = []
        for package in installed:
            resolved.append(package)
            deps = YumBase.INSTALL_DEPS
        for package in updated:
            resolved.append(package)
            deps = YumBase.UPDATE_DEPS
        for package in removed:
            resolved.append(package)
            deps = YumBase.REMOVE_DEPS
        self.assertEquals(len(report['resolved']), len(resolved))
        self.assertEquals(len(report['deps']), len(deps))

    def test_install(self):
        # Setup
        packages = [
            'zsh',
            'ksh',
            'gofer',
            'okaara',
        ]
        # Test
        package = self.Package()
        report = package.install(packages)
        # Verify
        self.verify(report, installed=packages)
        self.assertTrue(YumBase.processTransaction.called)

    def test_install_noapply(self):
        # Setup
        packages = [
            'zsh',
            'ksh',
            'gofer',
            'okaara',
        ]
        # Test
        package = self.Package(apply=False)
        report = package.install(packages)
        # Verify
        self.verify(report, installed=packages)
        self.assertFalse(YumBase.processTransaction.called)

    def test_install_importkeys(self):
        # Setup
        packages = [
            'zsh',
            'ksh',
            'gofer',
            'okaara',
        ]
        # Test
        package = self.Package(importkeys=True)
        report = package.install(packages)
        # Verify
        self.verify(report, installed=packages)
        self.assertTrue(YumBase.processTransaction.called)

    def test_install_notfound(self):
        # Setup
        packages = [
            'zsh',
            'ksh',
            'gofer',
            'okaara',
            YumBase.UNKNOWN_PKG,
        ]
        # Test & verify
        package = self.Package()
        self.assertRaises(Exception, package.install, [packages])
        self.assertFalse(YumBase.processTransaction.called)

    def test_update(self):
        # Setup
        packages = [
            'zsh',
            'ksh',
            'gofer',
            'okaara',
            ]
        # Test
        package = self.Package()
        report = package.update(packages)
        # Verify
        self.verify(report, installed=packages)
        self.assertTrue(YumBase.processTransaction.called)

    def test_update_noapply(self):
        # Setup
        packages = [
            'zsh',
            'ksh',
            'gofer',
            'okaara',
            ]
        # Test
        package = self.Package(apply=False)
        report = package.update(packages)
        # Verify
        self.verify(report, installed=packages)
        self.assertFalse(YumBase.processTransaction.called)

    def test_update_importkeys(self):
        # Setup
        packages = [
            'zsh',
            'ksh',
            'gofer',
            'okaara',
            ]
        # Test
        package = self.Package(importkeys=True)
        report = package.update(packages)
        # Verify
        self.verify(report, installed=packages)
        self.assertTrue(YumBase.processTransaction.called)

    def test_update_notfound(self):
        # Setup
        packages = [
            'zsh',
            'ksh',
            'gofer',
            'okaara',
            YumBase.UNKNOWN_PKG,
            ]
        # Test & verify
        package = self.Package()
        self.assertRaises(Exception, package.update, [packages])
        self.assertFalse(YumBase.processTransaction.called)

    def test_uninstall(self):
        # Setup
        packages = [
            'zsh',
            'ksh',
        ]
        # Test
        package = self.Package()
        report = package.uninstall(packages)
        # Verify
        self.verify(report, removed=packages)
        self.assertTrue(YumBase.processTransaction.called)

    def test_uninstall_noapply(self):
        # Setup
        packages = [
            'zsh',
            'ksh',
            ]
        # Test
        package = self.Package(apply=False)
        report = package.uninstall(packages)
        # Verify
        self.verify(report, removed=packages)
        self.assertFalse(YumBase.processTransaction.called)


class TestGroups(ToolTest):

    def verify(self, report, installed=[], removed=[]):
        resolved = []
        deps = []
        for group in installed:
            resolved += [str(p) for p in YumBase.GROUPS[group]]
            deps = YumBase.INSTALL_DEPS
        for group in removed:
            resolved += [str(p) for p in YumBase.GROUPS[group]]
            deps = YumBase.REMOVE_DEPS
        self.assertEquals(len(report['resolved']), len(resolved))
        self.assertEquals(len(report['deps']), len(deps))

    def test_install(self):
        # Setup
        groups = ['mygroup', 'pulp']
        # Test
        group = self.PackageGroup()
        report = group.install(groups)
        # Verify
        self.verify(report, installed=groups)
        self.assertTrue(YumBase.processTransaction.called)

    def test_install_importkeys(self):
        # Setup
        groups = ['mygroup', 'pulp']
        # Test
        group = self.PackageGroup(importkeys=True)
        report = group.install(groups)
        # Verify
        self.verify(report, installed=groups)
        self.assertTrue(YumBase.processTransaction.called)

    def test_install_noapply(self):
        # Setup
        groups = ['mygroup', 'pulp']
        # Test
        group = self.PackageGroup(apply=False)
        report = group.install(groups)
        # Verify
        self.verify(report, installed=groups)
        self.assertFalse(YumBase.processTransaction.called)

    def test_install_notfound(self):
        # Setup
        groups = ['mygroup', 'pulp', 'xxxx']
        # Test & verify
        group = self.PackageGroup()
        self.assertRaises(Exception, group.install, [groups])
        self.assertFalse(YumBase.processTransaction.called)

    def test_uninstall(self):
        # Setup
        groups = ['mygroup', 'pulp']
        # Test
        group = self.PackageGroup()
        report = group.install(groups)
        # Verify
        self.verify(report, removed=groups)
        self.assertTrue(YumBase.processTransaction.called)

    def test_uninstall_noapply(self):
        # Setup
        groups = ['mygroup', 'pulp']
        # Test
        group = self.PackageGroup(apply=False)
        report = group.install(groups)
        # Verify
        self.verify(report, removed=groups)
        self.assertFalse(YumBase.processTransaction.called)


class TestProgressReport(PulpRPMTests):

    def setUp(self):
        PulpRPMTests.setUp(self)
        from yum.callbacks import PT_MESSAGES
        from pulp_rpm.handler.rpmtools import\
            ProcessTransCallback,\
            RPMCallback,\
            DownloadCallback,\
            ProgressReport
        self.PT_MESSAGES = PT_MESSAGES
        self.ProcessTransCallback = ProcessTransCallback
        self.RPMCallback = RPMCallback
        self.DownloadCallback = DownloadCallback
        self.ProgressReport = ProgressReport

    def test_report_steps(self):
        STEPS = ('A', 'B', 'C')
        ACTION = ('downloading', 'package-xyz-1.0-1.f16.rpm')
        pr = self.ProgressReport()
        pr._updated = Mock()
        for s in STEPS:
            # validate steps pushed with status of None
            pr.push_step(s)
            name, status = pr.steps[-1]
            self.assertEqual(name, s)
            self.assertTrue(status is None)
            # validate details cleared on state pushed
            self.assertEqual(len(pr.details), 0)
            # set the action
            pr.set_action(ACTION[0], ACTION[1])
            # validate action
            self.assertEqual(pr.details['action'], ACTION[0])
            self.assertEqual(pr.details['package'], ACTION[1])
            # validate previous step status is set (True) on next
            # push when status is None
            prev = pr.steps[-2:-1]
            if prev:
                self.assertTrue(prev[0][1])

    def test_report_steps_with_errors(self):
        # Test that previous state with status=False is not
        # set (True) on next state push
        STEPS = ('A', 'B', 'C')
        pr = self.ProgressReport()
        pr._updated = Mock()
        pr.push_step(STEPS[0])
        pr.push_step(STEPS[1])
        pr.set_status(False)
        pr.push_step(STEPS[2])
        self.assertTrue(pr.steps[0][1])
        self.assertFalse(pr.steps[1][1])
        self.assertTrue(pr.steps[2][1] is None)

    def test_trans_callback(self):
        pr = self.ProgressReport()
        pr._updated = Mock()
        cb = self.ProcessTransCallback(pr)
        for state in sorted(self.PT_MESSAGES.keys()):
            cb.event(state)
        pr.set_status(True)
        self.assertEqual(len(self.PT_MESSAGES), len(pr.steps))
        i = 0
        for state in sorted(self.PT_MESSAGES.keys()):
            step = pr.steps[i]
            name = self.PT_MESSAGES[state]
            self.assertEqual(step[0], name)
            self.assertTrue(step[1])
            i += 1

    def test_rpm_callback(self):
        pr = self.ProgressReport()
        pr._updated = Mock()
        cb = self.RPMCallback(pr)
        for action in sorted(cb.action.keys()):
            package = '%s_package' % action
            cb.event(package, action)
            self.assertEqual(pr.details['action'], cb.action[action])
            self.assertEqual(pr.details['package'], package)
        self.assertEqual(len(pr.steps), 0)

    def test_download_callback(self):
        FILES = ('A', 'B', 'C')
        pr = self.ProgressReport()
        pr._updated = Mock()
        cb = self.DownloadCallback(pr)
        for file in FILES:
            path = '/path/%s' % file
            cb.start(filename=path, basename=file, size=1024)
            self.assertEqual(pr.details['action'], 'Downloading')
            self.assertEqual(pr.details['package'], '%s | 1.0 kB' % file)
        self.assertEqual(len(pr.steps), 0)
