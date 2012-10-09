
import sys
import os
import tempfile
import shutil

import mock_yum
from mock import Mock
from mock_yum import YumBase
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

    def verify_succeeded(self, report, installed=[], updated=[], removed=[], reboot=False):
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
        chgcnt = len(resolved) + len(deps)
        if reboot:
            chgcnt += 1
        self.assertEquals(report.chgcnt, chgcnt)
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
        self.verify_succeeded(report, installed=units, reboot=True)
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
        self.verify_succeeded(report, updated=units, reboot=True)
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
        self.verify_succeeded(report, removed=units, reboot=True)
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

    def verify_succeeded(self, report, installed=[], removed=[], reboot=False):
        resolved = []
        deps = []
        for group in installed:
            resolved += [str(p) for p in YumBase.GROUPS[group]]
            deps = YumBase.INSTALL_DEPS
        for group in removed:
            resolved += [str(p) for p in YumBase.GROUPS[group]]
            deps = YumBase.REMOVE_DEPS
        self.assertTrue(report.status)
        chgcnt = len(resolved)+len(deps)
        if reboot:
            chgcnt += 1
        self.assertEquals(report.chgcnt, chgcnt)
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
        self.verify_succeeded(report, installed=groups, reboot=True)
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
        self.verify_succeeded(report, removed=groups, reboot=True)
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
        # TODO: implement test
        pass


class TestLinux(HandlerTest):

    TYPE_ID = 'Linux'

    def setUp(self):
        HandlerTest.setUp(self)
        handler = self.container.find(self.TYPE_ID, role=SYSTEM)
        self.assertTrue(handler is not None, msg='%s handler not loaded' % self.TYPE_ID)

    def test_linux(self):
        # TODO: implement test
        pass
