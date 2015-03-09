import unittest

from mock import Mock

from pulp.agent.lib import container, dispatcher, report
from pulp.agent.lib.conduit import Conduit
from pulp.common.config import PropertyNotFound, SectionNotFound
from pulp.devel.mock_handlers import MockDeployer


class TestConduit(Conduit):

    class Test:
        def __init__(self):
            self.succeeded = True
            self.exception = None

    def __init__(self):
        self.test = self.Test()


class TestHandlerContainer(unittest.TestCase):

    def setUp(self):
        self.deployer = MockDeployer()
        self.deployer.deploy()

    def tearDown(self):
        self.deployer.clean()

    def container(self):
        return container.Container(MockDeployer.CONF_D, [MockDeployer.PATH])

    def test_loading(self):
        # Setup
        c = self.container()
        # Test
        c.load()
        # Verify
        handler = c.find('rpm')
        self.assertTrue(handler is not None)
        handler = c.find('srpm')
        self.assertTrue(handler is not None)
        handler = c.find('puppet')
        self.assertTrue(handler is None)
        handler = c.find('yum', container.BIND)
        self.assertTrue(handler is not None)
        handler = c.find('Linux', container.SYSTEM)
        self.assertTrue(handler is not None)
        errors = c.errors()
        self.assertEquals(len(errors), 3)
        self.assertTrue(isinstance(errors[0], ImportError))
        self.assertTrue(isinstance(errors[1], PropertyNotFound))
        self.assertTrue(isinstance(errors[2], SectionNotFound))

    def test_find(self):
        # Setup
        c = self.container()
        # Test
        c.load()
        handler = c.find('xxx')
        # Verify
        self.assertTrue(handler is None)


class TestDispatcher(unittest.TestCase):

    def setUp(self):
        self.deployer = MockDeployer()
        self.deployer.deploy()

    def tearDown(self):
        self.deployer.clean()

    def container(self):
        return container.Container(MockDeployer.CONF_D, [MockDeployer.PATH])

    def test_install(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='ksh'))
        units.append(unit)
        options = {}
        # Test
        conduit = Conduit()
        _report = d.install(conduit, units, options)
        self.assertTrue(_report.succeeded)
        self.assertEquals(_report.num_changes, 2)
        self.assertFalse(_report.reboot['scheduled'])

    def test_install_failed(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='ksh'))
        units.append(unit)
        handler = d.container.find('rpm')
        _report = report.ContentReport()
        _report.set_failed({'a': 1})
        handler.install = Mock(return_value=_report)
        # Test
        options = {}
        conduit = Conduit()
        _report = d.install(conduit, units, options)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)
        self.assertFalse(_report.reboot['scheduled'])
        self.assertFalse(_report.details['rpm']['succeeded'])
        self.assertEqual(_report.details['rpm']['details'], {'a': 1})

    def test_install_raised(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='ksh'))
        units.append(unit)
        handler = d.container.find('rpm')
        handler.install = Mock(side_effect=ValueError())
        # Test
        options = {}
        conduit = Conduit()
        _report = d.install(conduit, units, options)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)
        self.assertFalse(_report.reboot['scheduled'])
        self.assertFalse(_report.details['rpm']['succeeded'])
        self.assertTrue('message' in _report.details['rpm']['details'])
        self.assertTrue('trace' in _report.details['rpm']['details'])

    def test_install_reboot(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        options = dict(reboot=True)
        # Test
        conduit = Conduit()
        _report = d.install(conduit, [unit], options)
        self.assertTrue(_report.succeeded)
        self.assertEquals(_report.num_changes, 2)
        self.assertTrue(_report.reboot['scheduled'])

    def test_install_failed_no_handler(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='xxx',
            unit_key=dict(name='ksh'))
        units.append(unit)
        options = {}
        # Test
        conduit = Conduit()
        _report = d.install(conduit, units, options)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 1)
        # RPM passed
        rpm = _report.details['rpm']
        self.assertTrue(rpm['succeeded'])
        # XXX failed
        xxx = _report.details['xxx']
        self.assertFalse(xxx['succeeded'])

    def test_update(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='ksh'))
        units.append(unit)
        options = {}
        # Test
        conduit = Conduit()
        _report = d.update(conduit, units, options)
        self.assertTrue(_report.succeeded)
        self.assertEquals(_report.num_changes, 2)

    def test_update_failed(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='ksh'))
        units.append(unit)
        handler = d.container.find('rpm')
        _report = report.ContentReport()
        _report.set_failed({'a': 1})
        handler.update = Mock(return_value=_report)
        # Test
        options = {}
        conduit = Conduit()
        _report = d.update(conduit, units, options)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)
        self.assertFalse(_report.reboot['scheduled'])
        self.assertFalse(_report.details['rpm']['succeeded'])
        self.assertEqual(_report.details['rpm']['details'], {'a': 1})

    def test_update_raised(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='ksh'))
        units.append(unit)
        handler = d.container.find('rpm')
        handler.update = Mock(side_effect=ValueError())
        # Test
        options = {}
        conduit = Conduit()
        _report = d.update(conduit, units, options)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)
        self.assertFalse(_report.reboot['scheduled'])
        self.assertFalse(_report.details['rpm']['succeeded'])
        self.assertTrue('message' in _report.details['rpm']['details'])
        self.assertTrue('trace' in _report.details['rpm']['details'])

    def test_uninstall(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        options = {}
        # Test
        conduit = Conduit()
        _report = d.uninstall(conduit, [unit], options)
        self.assertTrue(_report.succeeded)
        self.assertEquals(_report.num_changes, 1)

    def test_uninstall_failed(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='ksh'))
        units.append(unit)
        handler = d.container.find('rpm')
        _report = report.ContentReport()
        _report.set_failed({'a': 1})
        handler.uninstall = Mock(return_value=_report)
        # Test
        options = {}
        conduit = Conduit()
        _report = d.uninstall(conduit, units, options)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)
        self.assertFalse(_report.reboot['scheduled'])
        self.assertFalse(_report.details['rpm']['succeeded'])
        self.assertEqual(_report.details['rpm']['details'], {'a': 1})

    def test_uninstall_raised(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        units = []
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='zsh'))
        units.append(unit)
        unit = dict(
            type_id='rpm',
            unit_key=dict(name='ksh'))
        units.append(unit)
        handler = d.container.find('rpm')
        handler.uninstall = Mock(side_effect=ValueError())
        # Test
        options = {}
        conduit = Conduit()
        _report = d.uninstall(conduit, units, options)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)
        self.assertFalse(_report.reboot['scheduled'])
        self.assertFalse(_report.details['rpm']['succeeded'])
        self.assertTrue('message' in _report.details['rpm']['details'])
        self.assertTrue('trace' in _report.details['rpm']['details'])

    def test_profile(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        # Test
        conduit = Conduit()
        _report = d.profile(conduit)
        self.assertTrue(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)

    def test_profile_failed(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        handler = d.container.find('rpm')
        _report = report.ProfileReport()
        _report.set_failed({'a': 1})
        handler.profile = Mock(return_value=_report)
        # Test
        conduit = Conduit()
        _report = d.profile(conduit)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)
        self.assertFalse(_report.details['rpm']['succeeded'])
        self.assertEqual(_report.details['rpm']['details'], {'a': 1})

    def test_profile_raised(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        handler = d.container.find('rpm')
        handler.profile = Mock(side_effect=ValueError())
        # Test
        conduit = Conduit()
        _report = d.profile(conduit)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)
        self.assertFalse(_report.details['rpm']['succeeded'])
        self.assertTrue('message' in _report.details['rpm']['details'])
        self.assertTrue('trace' in _report.details['rpm']['details'])

    def test_reboot(self):
        # Setup
        d = dispatcher.Dispatcher(self.container())
        # Test
        conduit = Conduit()
        _report = d.reboot(conduit, {})
        self.assertTrue(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)

    def test_bind(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id, details={})
        options = {}
        _report = d.bind(conduit, [binding], options)
        self.assertTrue(_report.succeeded)
        self.assertEqual(_report.num_changes, 1)
        details = _report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertTrue(details['succeeded'])
        self.assertEqual(details['details'], {})

    def test_bind_failed(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        handler = d.container.find(type_id, container.BIND)
        _report = report.BindReport(repo_id)
        _report.set_failed({'a': 1})
        handler.bind = Mock(return_value=_report)
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id, details={})
        options = {}
        _report = d.bind(conduit, [binding], options)
        self.assertFalse(_report.succeeded)
        self.assertEqual(_report.num_changes, 0)
        details = _report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertFalse(details['succeeded'])
        self.assertEqual(details['details'], {'a': 1})

    def test_bind_raised(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        handler = d.container.find(type_id, container.BIND)
        handler.bind = Mock(side_effect=ValueError())
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id, details={})
        options = {}
        _report = d.bind(conduit, [binding], options)
        self.assertFalse(_report.succeeded)
        self.assertEqual(_report.num_changes, 0)
        details = _report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertTrue('message' in details['details'])
        self.assertTrue('trace' in details['details'])

    def test_unbind(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id)
        options = {}
        _report = d.unbind(conduit, [binding], options)
        self.assertTrue(_report.succeeded)
        self.assertEqual(_report.num_changes, 1)
        details = _report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertEqual(details['details'], {})

    def test_unbind_failed(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        handler = d.container.find(type_id, container.BIND)
        _report = report.BindReport(repo_id)
        _report.set_failed({'a': 1})
        handler.unbind = Mock(return_value=_report)
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id)
        options = {}
        _report = d.unbind(conduit, [binding], options)
        self.assertFalse(_report.succeeded)
        self.assertEqual(_report.num_changes, 0)
        details = _report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertFalse(details['succeeded'])
        self.assertEqual(details['details'], {'a': 1})

    def test_unbind_raised(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        handler = d.container.find(type_id, container.BIND)
        handler.unbind = Mock(side_effect=ValueError)
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id)
        options = {}
        _report = d.unbind(conduit, [binding], options)
        self.assertFalse(_report.succeeded)
        self.assertEqual(_report.num_changes, 0)
        details = _report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertFalse(details['succeeded'])
        self.assertTrue('message' in details['details'])
        self.assertTrue('trace' in details['details'])

    def test_unbind_all(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        # Test
        conduit = Conduit()
        binding = dict(type_id=None, repo_id=repo_id)
        options = {}
        _report = d.unbind(conduit, [binding], options)
        self.assertTrue(_report.succeeded)
        self.assertEqual(_report.num_changes, 1)
        details = _report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertEqual(details['details'], {})

    def test_unbind_all_failed(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        handler = d.container.find(type_id, container.BIND)
        _report = report.BindReport(repo_id)
        _report.set_failed({'a': 1})
        handler.unbind = Mock(return_value=_report)
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id)
        options = {}
        _report = d.unbind(conduit, [binding], options)
        self.assertFalse(_report.succeeded)
        self.assertEqual(_report.num_changes, 0)
        details = _report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertFalse(details['succeeded'])
        self.assertEqual(details['details'], {'a': 1})

    def test_unbind_all_raised(self):
        type_id = 'yum'
        repo_id = 'repo-1'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        handler = d.container.find(type_id, container.BIND)
        handler.unbind = Mock(side_effect=ValueError)
        # Test
        conduit = Conduit()
        binding = dict(type_id=type_id, repo_id=repo_id)
        options = {}
        _report = d.unbind(conduit, [binding], options)
        self.assertFalse(_report.succeeded)
        self.assertEqual(_report.num_changes, 0)
        details = _report.details[type_id][0]
        self.assertEqual(details['repo_id'], repo_id)
        self.assertFalse(details['succeeded'])
        self.assertTrue('message' in details['details'])
        self.assertTrue('trace' in details['details'])

    def test_clean(self):
        type_id = 'yum'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        # Test
        conduit = Conduit()
        _report = d.clean(conduit)
        self.assertTrue(_report.succeeded)
        self.assertEquals(_report.num_changes, 1)
        details = _report.details[type_id]
        self.assertEqual(details['details'], {})

    def test_clean_failed(self):
        type_id = 'yum'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        handler = d.container.find(type_id, container.BIND)
        _report = report.CleanReport()
        _report.set_failed({'a': 1})
        handler.clean = Mock(return_value=_report)
        # Test
        conduit = Conduit()
        _report = d.clean(conduit)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)
        details = _report.details[type_id]
        self.assertEqual(details['details'], {'a': 1})

    def test_clean_raised(self):
        type_id = 'yum'
        # Setup
        d = dispatcher.Dispatcher(self.container())
        handler = d.container.find(type_id, container.BIND)
        handler.clean = Mock(side_effect=ValueError)
        # Test
        conduit = Conduit()
        _report = d.clean(conduit)
        self.assertFalse(_report.succeeded)
        self.assertEquals(_report.num_changes, 0)
        details = _report.details[type_id]
        self.assertTrue('message' in details['details'])
        self.assertTrue('trace' in details['details'])
