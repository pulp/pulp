import unittest

from pulp.server.managers import factory
from pulp.server.managers.auth.authentication import AuthenticationManager
from pulp.server.managers.auth.cert.cert_generator import CertGenerationManager
from pulp.server.managers.auth.cert.certificate import CertificateManager
from pulp.server.managers.auth.password import PasswordManager
from pulp.server.managers.auth.permission.cud import PermissionManager
from pulp.server.managers.auth.permission.query import PermissionQueryManager
from pulp.server.managers.auth.role.cud import RoleManager
from pulp.server.managers.auth.role.query import RoleQueryManager
from pulp.server.managers.auth.user.cud import UserManager
from pulp.server.managers.auth.user.query import UserQueryManager
from pulp.server.managers.consumer.cud import ConsumerManager
from pulp.server.managers.content.cud import ContentManager
from pulp.server.managers.content.query import ContentQueryManager
from pulp.server.managers.content.upload import ContentUploadManager
from pulp.server.managers.event.remote import TopicPublishManager
from pulp.server.managers.repo.unit_association import RepoUnitAssociationManager


class FactoryTests(unittest.TestCase):

    def clean(self):
        factory.reset()

    def test_syntactic_sugar_methods(self):
        """
        Tests the syntactic sugar methods for retrieving specific managers.
        """
        # Setup
        factory.initialize()

        # Test
        self.assertTrue(isinstance(factory.authentication_manager(), AuthenticationManager))
        self.assertTrue(isinstance(factory.cert_generation_manager(), CertGenerationManager))
        self.assertTrue(isinstance(factory.certificate_manager(), CertificateManager))
        self.assertTrue(isinstance(factory.password_manager(), PasswordManager))
        self.assertTrue(isinstance(factory.permission_manager(), PermissionManager))
        self.assertTrue(isinstance(factory.permission_query_manager(), PermissionQueryManager))
        self.assertTrue(isinstance(factory.role_manager(), RoleManager))
        self.assertTrue(isinstance(factory.role_query_manager(), RoleQueryManager))
        self.assertTrue(isinstance(factory.user_manager(), UserManager))
        self.assertTrue(isinstance(factory.user_query_manager(), UserQueryManager))
        self.assertTrue(isinstance(factory.repo_unit_association_manager(),
                                   RepoUnitAssociationManager))
        self.assertTrue(isinstance(factory.content_manager(), ContentManager))
        self.assertTrue(isinstance(factory.content_query_manager(), ContentQueryManager))
        self.assertTrue(isinstance(factory.content_upload_manager(), ContentUploadManager))
        self.assertTrue(isinstance(factory.consumer_manager(), ConsumerManager))
        self.assertTrue(isinstance(factory.topic_publish_manager(), TopicPublishManager))

    def test_get_manager(self):
        """
        Tests retrieving a manager instance for a valid manager mapping.
        """

        # Setup
        factory.initialize()

        # Test
        manager = factory.get_manager(factory.TYPE_CONSUMER)

        # Verify
        self.assertTrue(manager is not None)
        self.assertTrue(isinstance(manager, ConsumerManager))

    def test_get_manager_invalid_type(self):
        """
        Tests retrieving a manager instance but passing a bad type ID.
        """

        # Test
        try:
            factory.get_manager('foo')
            self.fail('Invalid manager type did not raise an exception')
        except factory.InvalidType, e:
            self.assertEqual(e.type_key, 'foo')
            self.assertEqual(str(e), 'Invalid manager type requested [foo]')

    def test_register_and_reset(self):
        """
        Tests that registering a new class and resetting properly affects the
        class mappings.
        """

        # Setup
        class FakeManager:
            pass

        factory.register_manager(factory.TYPE_CONSUMER, FakeManager)

        # Test Register
        manager = factory.get_manager(factory.TYPE_CONSUMER)
        self.assertTrue(isinstance(manager, FakeManager))

        # Test Reset
        factory.reset()
        manager = factory.get_manager(factory.TYPE_CONSUMER)
        self.assertTrue(isinstance(manager, ConsumerManager))
