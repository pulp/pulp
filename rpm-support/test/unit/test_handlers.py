
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


class TestHandlers(TestCase):

    def setUp(self):
        mock_yum.install()
        self.deployer = Deployer()
        dpath, hpath = self.deployer.install()
        container = Container(root=dpath, path=[hpath])
        self.dispatcher = Dispatcher(container)
        os.system = Mock()

    def tearDown(self):
        self.deployer.uninstall()

    def validate(self, report, installed=None, updated=None, removed=None):
        self.assertTrue(report.status)
        self.assertEquals(report.chgcnt, 3)
        self.assertEquals(len(report.details), 1)
        report = report.details['rpm']
        self.assertTrue(report['status'])
        self.assertEquals(len(report['details']['resolved']), 1)
        if installed:
            deps = YumBase.INSTALL_DEPS
        elif updated:
            deps = YumBase.UPDATE_DEPS
        elif removed:
            deps = YumBase.REMOVE_DEPS
        self.assertEquals(len(report['details']['deps']), len(deps))

    def test_install(self):
        units = [
            {'type_id':'rpm', 'unit_key':{'name':'zsh'}},
            {'type_id':'rpm', 'unit_key':{'name':'ksh'}},
            {'type_id':'rpm', 'unit_key':{'name':'gofer'}},
            {'type_id':'rpm', 'unit_key':{'name':'okaara'}},
        ]
        report = self.dispatcher.install(units, {})
        self.validate(report, installed=units)
        self.assertFalse(report.reboot['scheduled'])

    def test_install_reboot(self):
        units = [
            {'type_id':'rpm', 'unit_key':{'name':'zsh'}},
            {'type_id':'rpm', 'unit_key':{'name':'ksh'}},
            {'type_id':'rpm', 'unit_key':{'name':'gofer'}},
            {'type_id':'rpm', 'unit_key':{'name':'okaara'}},
        ]
        options = {'reboot':True}
        report = self.dispatcher.install(units, options)
        self.validate(report, installed=units)
        self.assertTrue(report.reboot['scheduled'])

    def test_update(self):
        units = [
            {'type_id':'rpm', 'unit_key':{'name':'zsh'}},
            {'type_id':'rpm', 'unit_key':{'name':'ksh'}},
            {'type_id':'rpm', 'unit_key':{'name':'gofer'}},
            {'type_id':'rpm', 'unit_key':{'name':'okaara'}},
        ]
        report = self.dispatcher.update(units, {})
        self.validate(report, updated=units)

    def test_uninstall(self):
        units = [
            {'type_id':'rpm', 'unit_key':{'name':'zsh'}},
        ]
        report = self.dispatcher.uninstall(units, {})
        self.validate(report, removed=units)
