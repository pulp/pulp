from django.test import TestCase

from pulp.platform.models import Consumer


class TestConsumer(TestCase):

    def test_natural_key(self):
        consumer = Consumer(name='test')
        self.assertEqual(consumer.natural_key(), (consumer.name,))
