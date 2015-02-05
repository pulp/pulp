from .... import base
from pulp.server.managers import factory as manager_factory


class PasswordManagerTests(base.PulpServerTests):
    def setUp(self):
        super(PasswordManagerTests, self).setUp()
        self.password_manager = manager_factory.password_manager()

    def test_unicode_password(self):
        password = u"some password"
        hashed = self.password_manager.hash_password(password)
        self.assertNotEqual(hashed, password)

    def test_hash_password(self):
        password = "some password"
        hashed = self.password_manager.hash_password(password)
        self.assertNotEqual(hashed, password)

    def test_check_password(self):
        password = "some password"
        hashed = self.password_manager.hash_password(password)
        self.assertTrue(self.password_manager.check_password(hashed, password))
