from django.test import TestCase

from pulpcore.app.models import Consumer, Publisher, Repository


class TestConsumer(TestCase):

    def test_natural_key(self):
        consumer = Consumer(name='test')
        self.assertEqual(consumer.natural_key(), (consumer.name,))

    def test_bind(self):
        consumer = Consumer(name='test')
        consumer.save()
        repository = Repository(name='test')
        repository.save()
        publisher = Publisher(name='test', repository=repository)
        publisher.save()

        # bind
        consumer.publishers.add(publisher)
        consumer.save()

        # inspect publishers
        fetched = consumer.publishers.all()[0]
        self.assertEqual(fetched.id, publisher.id)

        # inspect consumers
        fetched = publisher.consumers.all()[0]
        self.assertEqual(fetched.id, consumer.id)
