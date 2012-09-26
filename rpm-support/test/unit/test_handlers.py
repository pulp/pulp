
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../platform/src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../rpm_support/src/")

import mock_yum
from mock import Mock
from mock_yum import YumBase
from unittest import TestCase
from rpm_support_base import PulpRPMTests
from pulp.agent.lib.container import Container, SYSTEM, CONTENT, BIND
from pulp.agent.lib.dispatcher import Dispatcher
from pulp.agent.lib.conduit import Conduit


class Deployer:

    def __init__(self):
        self.root = None
        self.cwd = os.path.abspath(os.path.dirname(__file__))

    def install(self):
        root = tempfile.mkdtemp()
        targets = \
            (os.path.join(root, 'descriptors'),
             os.path.join(root, 'handlers'))
        self.deploydescriptors(targets[0])
        self.deployhandlers(targets[1])
        self.root = root
        return targets

    def uninstall(self):
        shutil.rmtree(self.root, ignore_errors=True)
        self.root = None

    def deploydescriptors(self, target):
        os.makedirs(target)
        root = os.path.join(self.cwd, '../../etc/pulp/agent/conf.d/')
        for fn in os.listdir(root):
            path = os.path.join(root, fn)
            shutil.copy(path, target)

    def deployhandlers(self, target):
        os.makedirs(target)
        root = os.path.join(self.cwd, '../../handlers/')
        for fn in os.listdir(root):
            path = os.path.join(root, fn)
            shutil.copy(path, target)


class HandlerTest(PulpRPMTests):

    def setUp(self):
        PulpRPMTests.setUp(self)
        mock_yum.install()
        self.deployer = Deployer()
        dpath, hpath = self.deployer.install()
        self.container = Container(root=dpath, path=[hpath])
        self.dispatcher = Dispatcher(self.container)
        self.__system = os.system
        os.system = Mock()

    def tearDown(self):
        PulpRPMTests.tearDown(self)
        self.deployer.uninstall()
        os.system = self.__system
        YumBase.reset()


class TestPackages(HandlerTest):

    TYPE_ID = 'rpm'

    def setUp(self):
        HandlerTest.setUp(self)
        handler = self.container.find(self.TYPE_ID, role=CONTENT)
        self.assertTrue(handler is not None, msg='%s handler not loaded' % self.TYPE_ID)

    def verify_succeeded(self, report, installed=[], updated=[], removed=[]):
        resolved = []
        deps = []
        for unit in installed:
            resolved.append(unit)
            deps = YumBase.INSTALL_DEPS
        for unit in updated:
            resolved.append(unit)
            deps = YumBase.UPDATE_DEPS
        for unit in removed:
            resolved.append(unit)
            deps = YumBase.REMOVE_DEPS
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, len(resolved)+len(deps))
        self.assertEquals(len(report.details), 1)
        report = report.details[self.TYPE_ID]
        self.assertTrue(report['status'])
        self.assertEquals(len(report['details']['resolved']), len(resolved))
        self.assertEquals(len(report['details']['deps']), len(deps))

    def verify_failed(self, report):
        self.assertFalse(report.status)
        self.assertEquals(report.chgcnt, 0)
        self.assertEquals(len(report.details), 1)
        report = report.details[self.TYPE_ID]
        self.assertFalse(report['status'])
        self.assertTrue('message' in report['details'])
        self.assertTrue('trace' in report['details'])

    def test_install(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        conduit = Conduit()
        report = self.dispatcher.install(conduit, units, {})
        # Verify
        self.verify_succeeded(report, installed=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertTrue(YumBase.processTransaction.called)

    def test_install_noapply(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        conduit = Conduit()
        options = {'apply':False}
        report = self.dispatcher.install(conduit, units, options)
        # Verify
        self.verify_succeeded(report, installed=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertFalse(YumBase.processTransaction.called)
        
    def test_install_importkeys(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        conduit = Conduit()
        options = {'importkeys':True}
        report = self.dispatcher.install(conduit, units, options)
        # Verify
        self.verify_succeeded(report, installed=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertTrue(YumBase.processTransaction.called)

    def test_install_notfound(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':YumBase.UNKNOWN_PKG}},
        ]
        # Test
        conduit = Conduit()
        report = self.dispatcher.install(conduit, units, {})
        # Verify
        self.verify_failed(report)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertFalse(YumBase.processTransaction.called)

    def test_install_with_reboot(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        conduit = Conduit()
        options = {'reboot':True}
        report = self.dispatcher.install(conduit, units, options)
        # Verify
        self.verify_succeeded(report, installed=units)
        self.assertTrue(report.reboot['scheduled'])
        self.assertEquals(report.reboot['details']['minutes'], 1)
        os.system.assert_called_once_with('shutdown -r +1')
        self.assertTrue(YumBase.processTransaction.called)

    def test_update(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        conduit = Conduit()
        report = self.dispatcher.update(conduit, units, {})
        # Verify
        self.verify_succeeded(report, updated=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertTrue(YumBase.processTransaction.called)
        
    def test_update_noapply(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        conduit = Conduit()
        options = {'apply':False}
        report = self.dispatcher.update(conduit, units, options)
        # Verify
        self.verify_succeeded(report, updated=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertFalse(YumBase.processTransaction.called)
        
    def test_update_importkeys(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        conduit = Conduit()
        options = {'importkeys':True}
        report = self.dispatcher.update(conduit, units, options)
        # Verify
        self.verify_succeeded(report, updated=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertTrue(YumBase.processTransaction.called)

    def test_update_with_reboot(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        conduit = Conduit()
        options = {'reboot':True, 'minutes':5}
        report = self.dispatcher.update(conduit, units, options)
        # Verify
        self.verify_succeeded(report, updated=units)
        self.assertTrue(report.reboot['scheduled'])
        self.assertEquals(report.reboot['details']['minutes'], 5)
        os.system.assert_called_once_with('shutdown -r +5')
        self.assertTrue(YumBase.processTransaction.called)

    def test_uninstall(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        conduit = Conduit()
        report = self.dispatcher.uninstall(conduit, units, {})
        # Verify
        self.verify_succeeded(report, removed=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertTrue(YumBase.processTransaction.called)
        
    def test_uninstall_noapply(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        conduit = Conduit()
        options = {'apply':False}
        report = self.dispatcher.uninstall(conduit, units, options)
        # Verify
        self.verify_succeeded(report, removed=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertFalse(YumBase.processTransaction.called)

    def test_uninstall_with_reboot(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'kmod'}},
        ]
        # Test
        conduit = Conduit()
        options = {'reboot':True}
        report = self.dispatcher.uninstall(conduit, units, options)
        # Verify
        self.verify_succeeded(report, removed=units)
        self.assertTrue(report.reboot['scheduled'])
        self.assertEquals(report.reboot['details']['minutes'], 1)
        os.system.assert_called_once_with('shutdown -r +1')
        self.assertTrue(YumBase.processTransaction.called)


class TestGroups(HandlerTest):

    TYPE_ID = 'package_group'

    def setUp(self):
        HandlerTest.setUp(self)
        handler = self.container.find(self.TYPE_ID, role=CONTENT)
        self.assertTrue(handler is not None, msg='%s handler not loaded' % self.TYPE_ID)

    def verify_succeeded(self, report, installed=[], removed=[]):
        resolved = []
        deps = []
        for group in installed:
            resolved += [str(p) for p in YumBase.GROUPS[group]]
            deps = YumBase.INSTALL_DEPS
        for group in removed:
            resolved += [str(p) for p in YumBase.GROUPS[group]]
            deps = YumBase.REMOVE_DEPS
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, len(resolved)+len(deps))
        self.assertEquals(len(report.details), 1)
        report = report.details[self.TYPE_ID]
        self.assertTrue(report['status'])
        self.assertEquals(len(report['details']['resolved']), len(resolved))
        self.assertEquals(len(report['details']['deps']), len(deps))

    def verify_failed(self, report):
        self.assertFalse(report.status)
        self.assertEquals(report.chgcnt, 0)
        self.assertEquals(len(report.details), 1)
        report = report.details[self.TYPE_ID]
        self.assertFalse(report['status'])
        self.assertTrue('message' in report['details'])
        self.assertTrue('trace' in report['details'])

    def test_install(self):
        # Setup
        groups = ['mygroup', 'pulp']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        conduit = Conduit()
        report = self.dispatcher.install(conduit, units, {})
        # Verify
        self.verify_succeeded(report, installed=groups)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertTrue(YumBase.processTransaction.called)
        
    def test_install_importkeys(self):
        # Setup
        groups = ['mygroup', 'pulp']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        conduit = Conduit()
        options = {'importkeys':True}
        report = self.dispatcher.install(conduit, units, options)
        # Verify
        self.verify_succeeded(report, installed=groups)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertTrue(YumBase.processTransaction.called)
        
    def test_install_noapply(self):
        # Setup
        groups = ['mygroup', 'pulp']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        conduit = Conduit()
        options = {'apply':False}
        report = self.dispatcher.install(conduit, units, options)
        # Verify
        self.verify_succeeded(report, installed=groups)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertFalse(YumBase.processTransaction.called)

    def test_install_notfound(self):
        # Setup
        groups = ['mygroup', 'pulp', 'xxxx']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        conduit = Conduit()
        report = self.dispatcher.install(conduit, units, {})
        # Verify
        self.verify_failed(report)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertFalse(YumBase.processTransaction.called)

    def test_install_with_reboot(self):
        # Setup
        groups = ['mygroup']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        conduit = Conduit()
        options = {'reboot':True}
        report = self.dispatcher.install(conduit, units, options)
        # Verify
        self.verify_succeeded(report, installed=groups)
        self.assertTrue(report.reboot['scheduled'])
        self.assertEquals(report.reboot['details']['minutes'], 1)
        os.system.assert_called_once_with('shutdown -r +1')
        self.assertTrue(YumBase.processTransaction.called)

    def test_uninstall(self):
        # Setup
        groups = ['mygroup', 'pulp']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        conduit = Conduit()
        report = self.dispatcher.uninstall(conduit, units, {})
        # Verify
        self.verify_succeeded(report, removed=groups)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertTrue(YumBase.processTransaction.called)
        
    def test_uninstall_noapply(self):
        # Setup
        groups = ['mygroup', 'pulp']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        conduit = Conduit()
        options = {'apply':False}
        report = self.dispatcher.uninstall(conduit, units, options)
        # Verify
        self.verify_succeeded(report, removed=groups)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        self.assertFalse(YumBase.processTransaction.called)

    def test_uninstall_with_reboot(self):
        # Setup
        groups = ['mygroup']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        conduit = Conduit()
        options = {'reboot':True}
        report = self.dispatcher.uninstall(conduit, units, options)
        # Verify
        self.verify_succeeded(report, removed=groups)
        self.assertTrue(report.reboot['scheduled'])
        self.assertEquals(report.reboot['details']['minutes'], 1)
        os.system.assert_called_once_with('shutdown -r +1')
        self.assertTrue(YumBase.processTransaction.called)


class TestBind(HandlerTest):

    TYPE_ID = 'yum_distributor'

    def setUp(self):
        HandlerTest.setUp(self)
        handler = self.container.find(self.TYPE_ID, role=BIND)
        self.assertTrue(handler is not None, msg='%s handler not loaded' % self.TYPE_ID)

    def test_bind(self):
        pass


class TestLinux(HandlerTest):

    TYPE_ID = 'Linux'

    def setUp(self):
        HandlerTest.setUp(self)
        handler = self.container.find(self.TYPE_ID, role=SYSTEM)
        self.assertTrue(handler is not None, msg='%s handler not loaded' % self.TYPE_ID)

    def test_linux(self):
        pass


class TestProgressReport(TestCase):

    def setUp(self):
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
