import unittest

from pulp.server.event import mail, notifiers, http


class TestNotifiers(unittest.TestCase):
    def test_http_type_present(self):
        ret = notifiers.get_notifier_function(http.TYPE_ID)
        self.assertTrue(callable(ret))
        self.assertEqual(ret, http.handle_event)

    def test_mail_type_present(self):
        ret = notifiers.get_notifier_function(mail.TYPE_ID)
        self.assertTrue(callable(ret))
        self.assertEqual(ret, mail.handle_event)

    def test_validator(self):
        self.assertTrue(notifiers.is_valid_notifier_type_id(mail.TYPE_ID))
        self.assertTrue(notifiers.is_valid_notifier_type_id(http.TYPE_ID))
        self.assertFalse(notifiers.is_valid_notifier_type_id(''))
        self.assertFalse(notifiers.is_valid_notifier_type_id(123))
        self.assertFalse(notifiers.is_valid_notifier_type_id('lhferlihfd'))
