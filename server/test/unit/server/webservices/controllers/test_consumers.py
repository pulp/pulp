"""
Test the pulp.server.webservices.controllers.consumers module.
"""
from .... import base
from pulp.devel import mock_plugins
from pulp.plugins.loader import api as plugin_api
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.managers import factory


class ConsumerTest(base.PulpWebserviceTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'dist-1'
    NOTIFY_AGENT = True
    BINDING_CONFIG = {'b': 'b'}
    DISTRIBUTOR_TYPE_ID = 'mock-distributor'

    def setUp(self):
        super(ConsumerTest, self).setUp()
        Consumer.get_collection().remove(safe=True)
        Repo.get_collection().remove(safe=True)
        RepoDistributor.get_collection().remove(safe=True)
        Bind.get_collection().remove(safe=True)
        plugin_api._create_manager()
        mock_plugins.install()

    def tearDown(self):
        super(ConsumerTest, self).tearDown()
        Consumer.get_collection().remove(safe=True)
        Repo.get_collection().remove(safe=True)
        RepoDistributor.get_collection().remove(safe=True)
        Bind.get_collection().remove(safe=True)
        mock_plugins.reset()


class ConsumersTest(base.PulpWebserviceTests):

    CONSUMER_IDS = ('test-consumer_1', 'test-consumer_2')
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'dist-1'
    NOTIFY_AGENT = True
    BINDING_CONFIG = {'c': 'c'}
    DISTRIBUTOR_TYPE_ID = 'mock-distributor'
    PROFILE = [{'name': 'zsh', 'version': '1.0'}, {'name': 'ksh', 'version': '1.0'}]

    def setUp(self):
        base.PulpWebserviceTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()

    def tearDown(self):
        base.PulpWebserviceTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def populate(self, bindings=False, profiles=False):
        if bindings:
            manager = factory.repo_manager()
            manager.create_repo(self.REPO_ID)
            manager = factory.repo_distributor_manager()
            manager.add_distributor(
                self.REPO_ID,
                self.DISTRIBUTOR_TYPE_ID,
                {},
                True,
                distributor_id=self.DISTRIBUTOR_ID)
        for consumer_id in self.CONSUMER_IDS:
            manager = factory.consumer_manager()
            manager.register(consumer_id)
            if bindings:
                manager = factory.consumer_bind_manager()
                manager.bind(consumer_id, self.REPO_ID, self.DISTRIBUTOR_ID,
                             self.NOTIFY_AGENT, self.BINDING_CONFIG)
        if profiles:
            manager = factory.consumer_profile_manager()
            for consumer_id in self.CONSUMER_IDS:
                manager.create(consumer_id, 'rpm', self.PROFILE)

    def validate(self, body, bindings=False, profiles=False):
        if bindings:
            self.assertEqual(len(self.CONSUMER_IDS), len(body))
            fetched = dict([(c['id'], c) for c in body])
            for consumer_id in self.CONSUMER_IDS:
                consumer = fetched[consumer_id]
                self.assertEquals(consumer['id'], consumer_id)
                self.assertTrue('_href' in consumer)
                self.assertTrue('bindings' in consumer)
                bindings = consumer['bindings']
                self.assertEquals(len(bindings), 1)
                self.assertEquals(bindings[0]['consumer_id'], consumer_id)
                self.assertEquals(bindings[0]['repo_id'], self.REPO_ID)
                self.assertEquals(bindings[0]['distributor_id'], self.DISTRIBUTOR_ID)
                self.assertEquals(bindings[0]['deleted'], False)
                self.assertEquals(bindings[0]['consumer_actions'], [])
        elif profiles:
            self.assertEqual(len(self.CONSUMER_IDS), len(body))
            fetched = dict([(c['consumer_id'], c) for c in body])
            for consumer_id in self.CONSUMER_IDS:
                consumer = fetched[consumer_id]
                self.assertEquals(consumer['consumer_id'], consumer_id)
                self.assertTrue('profile' in consumer)
        else:
            self.assertEqual(len(self.CONSUMER_IDS), len(body))
            fetched = dict([(c['id'], c) for c in body])
            for consumer_id in self.CONSUMER_IDS:
                consumer = fetched[consumer_id]
                self.assertEquals(consumer['id'], consumer_id)
                self.assertTrue('_href' in consumer)
                self.assertFalse('bindings' in body)


class TestSearch(ConsumersTest):

    FILTER = {'id': {'$in': ConsumersTest.CONSUMER_IDS}}
    SORT = [('id', 'ascending')]
    CRITERIA = dict(filters=FILTER, sort=SORT)

    def test_get(self):
        # Setup
        self.populate()
        # Test
        status, body = self.get('/v2/consumers/search/')
        # Verify
        self.assertEqual(200, status)
        self.validate(body)

    def test_get_with_details(self):
        # Setup
        self.populate(True)
        # Test
        status, body = self.get('/v2/consumers/search/?details=1')
        # Verify
        self.assertEqual(200, status)
        self.validate(body, True)

    def test_get_with_bindings(self):
        # Setup
        self.populate(True)
        # Test
        status, body = self.get('/v2/consumers/search/?bindings=1')
        # Verify
        self.assertEqual(200, status)
        self.validate(body, True)

    def test_post(self):
        # Setup
        self.populate()
        # Test
        body = {'criteria': self.CRITERIA}
        status, body = self.post('/v2/consumers/search/', body)
        # Verify
        self.validate(body)

    def test_post_with_details(self):
        # Setup
        self.populate(True)
        # Test
        body = {'criteria': self.CRITERIA, 'details': True}
        status, body = self.post('/v2/consumers/search/', body)
        # Verify
        self.assertEqual(200, status)
        self.validate(body, True)

    def test_post_with_bindings(self):
        # Setup
        self.populate(True)
        # Test
        body = {'criteria': self.CRITERIA, 'bindings': True}
        status, body = self.post('/v2/consumers/search/', body)
        # Verify
        self.assertEqual(200, status)
        self.validate(body, True)


class TestProfileSearch(ConsumersTest):

    FILTER = {'consumer_id': {'$in': ConsumersTest.CONSUMER_IDS}}
    SORT = [('consumer_id', 'ascending')]
    CRITERIA = dict(filters=FILTER, sort=SORT)

    def test_get(self):
        # Setup
        self.populate(profiles=True)
        # Test
        status, body = self.get('/v2/consumers/profile/search/')
        # Verify
        self.assertEqual(200, status)
        self.validate(body, profiles=True)

    def test_post(self):
        # Setup
        self.populate(profiles=True)
        # Test
        body = {'criteria': self.CRITERIA}
        status, body = self.post('/v2/consumers/profile/search/', body)
        # Verify
        self.validate(body, profiles=True)


class BindTest(base.PulpWebserviceTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'dist-1'
    NOTIFY_AGENT = True
    BINDING_CONFIG = {'a': 'a'}
    DISTRIBUTOR_TYPE_ID = 'mock-distributor'
    QUERY = dict(
        consumer_id=CONSUMER_ID,
        repo_id=REPO_ID,
        distributor_id=DISTRIBUTOR_ID,
    )
    PAYLOAD = dict(
        server_name='pulp.redhat.com',
        relative_path='/repos/content/repoA',
        protocols=['https'],
        gpg_keys=['key1'],
        ca_cert='MY-CA',
        client_cert='MY-CLIENT-CERT')

    def setUp(self):
        base.PulpWebserviceTests.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_api._create_manager()
        mock_plugins.install()

    def tearDown(self):
        base.PulpWebserviceTests.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def populate(self):
        manager = factory.repo_manager()
        manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            self.DISTRIBUTOR_TYPE_ID,
            {},
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        mock_plugins.MOCK_DISTRIBUTOR.create_consumer_payload.return_value = self.PAYLOAD
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)

    def test_search(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID,
                     self.NOTIFY_AGENT, self.BINDING_CONFIG)
        manager.action_pending(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID,
            Bind.Action.BIND,
            '0')

        # Test
        criteria = {
            'filters': {'consumer_actions.status': {'$in': ['pending', 'failed']}}}
        path = '/v2/consumers/binding/search/'
        body = dict(criteria=criteria)
        status, body = self.post(path, body)

        # Verify
        self.assertEqual(status, 200)
        self.assertEqual(len(body), 1)
