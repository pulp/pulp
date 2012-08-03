
import sys
import os
import tempfile
import shutil
from mock import Mock
from unittest import TestCase

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../platform/src/")

import mock_yum
from mock_yum import YumBase
from pulp.agent.lib.container import Container
from pulp.agent.lib.dispatcher import Dispatcher


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


class HandlerTest(TestCase):

    def setUp(self):
        mock_yum.install()
        self.deployer = Deployer()
        dpath, hpath = self.deployer.install()
        container = Container(root=dpath, path=[hpath])
        self.dispatcher = Dispatcher(container)
        self.__system = os.system
        os.system = Mock()

    def tearDown(self):
        self.deployer.uninstall()
        os.system = self.__system
        YumBase.reset()

class TestPackges(HandlerTest):

    TYPE_ID = 'rpm'

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
        report = self.dispatcher.install(units, {})
        # Verify
        self.verify_succeeded(report, installed=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        YumBase.processTransaction.assert_called_once_with()

    def test_install_noapply(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        options = {'apply':False}
        report = self.dispatcher.install(units, options)
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
        options = {'importkeys':True}
        report = self.dispatcher.install(units, options)
        # Verify
        self.verify_succeeded(report, installed=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        YumBase.processTransaction.assert_called_once_with()

    def test_install_notfound(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':YumBase.UNKNOWN_PKG}},
        ]
        # Test
        report = self.dispatcher.install(units, {})
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
        options = {'reboot':True}
        report = self.dispatcher.install(units, options)
        # Verify
        self.verify_succeeded(report, installed=units)
        self.assertTrue(report.reboot['scheduled'])
        self.assertEquals(report.reboot['details']['minutes'], 1)
        os.system.assert_called_once_with('shutdown -r +1')
        YumBase.processTransaction.assert_called_once_with()

    def test_update(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        report = self.dispatcher.update(units, {})
        # Verify
        self.verify_succeeded(report, updated=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        YumBase.processTransaction.assert_called_once_with()
        
    def test_update_noapply(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        options = {'apply':False}
        report = self.dispatcher.update(units, options)
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
        options = {'importkeys':True}
        report = self.dispatcher.update(units, options)
        # Verify
        self.verify_succeeded(report, updated=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        YumBase.processTransaction.assert_called_once_with()

    def test_update_with_reboot(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'ksh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'gofer'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        options = {'reboot':True, 'minutes':5}
        report = self.dispatcher.update(units, options)
        # Verify
        self.verify_succeeded(report, updated=units)
        self.assertTrue(report.reboot['scheduled'])
        self.assertEquals(report.reboot['details']['minutes'], 5)
        os.system.assert_called_once_with('shutdown -r +5')
        YumBase.processTransaction.assert_called_once_with()

    def test_uninstall(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        report = self.dispatcher.uninstall(units, {})
        # Verify
        self.verify_succeeded(report, removed=units)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        YumBase.processTransaction.assert_called_once_with()
        
    def test_uninstall_noapply(self):
        # Setup
        units = [
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'zsh'}},
            {'type_id':self.TYPE_ID, 'unit_key':{'name':'okaara'}},
        ]
        # Test
        options = {'apply':False}
        report = self.dispatcher.uninstall(units, options)
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
        options = {'reboot':True}
        report = self.dispatcher.uninstall(units, options)
        # Verify
        self.verify_succeeded(report, removed=units)
        self.assertTrue(report.reboot['scheduled'])
        self.assertEquals(report.reboot['details']['minutes'], 1)
        os.system.assert_called_once_with('shutdown -r +1')
        YumBase.processTransaction.assert_called_once_with()


class TestGroups(HandlerTest):

    TYPE_ID = 'package_group'

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
        report = self.dispatcher.install(units, {})
        # Verify
        self.verify_succeeded(report, installed=groups)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        YumBase.processTransaction.assert_called_once_with()
        
    def test_install_importkeys(self):
        # Setup
        groups = ['mygroup', 'pulp']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        options = {'importkeys':True}
        report = self.dispatcher.install(units, options)
        # Verify
        self.verify_succeeded(report, installed=groups)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        YumBase.processTransaction.assert_called_once_with()
        
    def test_install_noapply(self):
        # Setup
        groups = ['mygroup', 'pulp']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        options = {'apply':False}
        report = self.dispatcher.install(units, options)
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
        report = self.dispatcher.install(units, {})
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
        options = {'reboot':True}
        report = self.dispatcher.install(units, options)
        # Verify
        self.verify_succeeded(report, installed=groups)
        self.assertTrue(report.reboot['scheduled'])
        self.assertEquals(report.reboot['details']['minutes'], 1)
        os.system.assert_called_once_with('shutdown -r +1')
        YumBase.processTransaction.assert_called_once_with()

    def test_uninstall(self):
        # Setup
        groups = ['mygroup', 'pulp']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        report = self.dispatcher.uninstall(units, {})
        # Verify
        self.verify_succeeded(report, removed=groups)
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(report.reboot['scheduled'])
        self.assertFalse(os.system.called)
        YumBase.processTransaction.assert_called_once_with()
        
    def test_uninstall_noapply(self):
        # Setup
        groups = ['mygroup', 'pulp']
        units = [dict(type_id=self.TYPE_ID, unit_key=dict(name=g)) for g in groups]
        # Test
        options = {'apply':False}
        report = self.dispatcher.uninstall(units, options)
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
        options = {'reboot':True}
        report = self.dispatcher.uninstall(units, options)
        # Verify
        self.verify_succeeded(report, removed=groups)
        self.assertTrue(report.reboot['scheduled'])
        self.assertEquals(report.reboot['details']['minutes'], 1)
        os.system.assert_called_once_with('shutdown -r +1')
        YumBase.processTransaction.assert_called_once_with()


class TestBind(TestCase):
    # TBD
    pass