import os
import sys

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

from unittest import TestCase
from gopher.messaging.decorators import *
from gopher.messaging.base import Agent
from gopher.messaging.base import Container
from gopher.messaging.store import PendingQueue
from gopher.messaging.consumer import RequestConsumer
from gopher.messaging.async import ReplyConsumer, Listener
from gopher.messaging.producer import Producer
from gopher.messaging import Queue
from time import sleep
import logging

logging.root.setLevel(logging.ERROR)


PendingQueue.ROOT = '/tmp/pulp/messaging'


@remote
@alias('dog')
class Dog:

    WAG = 'WAG'
    WAGMSG = 'Yes master.  I will wag my tail because that is what dogs do.'
    BRKMSG = 'Yes master.  I will bark because that is what dogs do. "%s"'

    @remotemethod
    def bark(self, words):
        return self.BRKMSG % words

    @remotemethod
    def wag(self, n):
        wags = []
        for i in range(0, n):
            wags.append(self.WAG)
        return (wags, self.WAGMSG)

    def notpermitted(self):
        pass


class TestAgent(Agent):

    def __init__(self, id):
        queue = Queue(id)
        con = RequestConsumer(queue)
        Agent.__init__(self, con)


class RemoteAgent(Container):

    def __init__(self, id, **options):
        self.__producer = Producer()
        Container.__init__(self, id, self.__producer, **options)


class TestListener(Listener):

    def __init__(self):
        self.replies = []
        self.statuses = []

    def succeeded(self, reply):
        self.replies.append(reply.retval)

    def failed(self, reply):
        self.replies.append(reply.exval)

    def status(self, reply):
        self.statuses.append(reply.status)


class TestMessaging(TestCase):

    ID = '__pyunit'
    CTAG = '__pyunit_ctag'
    WAGS = 3

    def testSynchronous(self):
        results = []
        __agent = TestAgent(self.ID)
        agent = RemoteAgent(self.ID)
        dog = agent.Dog()
        r = agent.dog.bark('pulp rocks!')
        results.append(r)
        r = dog.wag(self.WAGS)
        results.append(r)
        self.validate(results)
        agent.close()

    def testAsynchronous(self):
        __agent = TestAgent(self.ID)
        agent = RemoteAgent(self.ID, ctag=self.CTAG)
        async = ReplyConsumer(Queue(self.CTAG))
        lnr = TestListener()
        async.start(lnr)
        dog = agent.Dog()
        dog.bark('pulp rocks!')
        dog.wag(self.WAGS)
        sleep(3)
        self.validate(lnr.replies)
        agent.close()
        async.close()

    def testExceptions(self):
        raised = 0
        __agent = TestAgent(self.ID)
        agent = RemoteAgent(self.ID)
        dog = agent.Dog()
        # class not found
        try:
            cat = agent.Cat()
            cat.foo()
        except Exception:
            raised += 1
        # method not found
        try:
            dog.foo()
        except Exception:
            raised += 1
        self.assertEqual(raised, 2)
        agent.close()

    def validate(self, results):
        # dog.bark()
        result = results[0]
        self.assertTrue(result.startswith(Dog.BRKMSG[:12]))
        # dog.wag()
        wags, msg = results[1]
        self.assertEquals(len(wags), self.WAGS)
        self.assertTrue(Dog.WAG in wags)
        self.assertTrue(msg.startswith(Dog.WAGMSG[:12]))
