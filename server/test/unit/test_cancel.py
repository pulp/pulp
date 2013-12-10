# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from threading import Thread
from unittest import TestCase

from pulp.server.cancel import Call


class Dog(object):

    def __init__(self):
        self.bark_count = 0
        self.canceled = False

    def bark(self, something):
        while not Call.current_canceled():
            self.bark_count += 1
        self.canceled = Call.current_canceled()


def bark(something):
    while not Call.current_canceled():
        if callable(something):
            return something()


def wag():
    while not Call.current_canceled():
        pass  # wag


class TestCall(TestCase):

    def verify(self, call, depth=1):
        self.assertEqual(call, Call.current())
        self.assertEqual(len(Call._current.stack), depth)
        self.assertEqual(Call._current.stack[-1], call.id)
        self.assertEqual(len(Call._calls), depth)
        self.assertFalse(Call._calls[call.id].canceled)
        return Call.current_canceled()

    def test_call(self):
        call = Call(self.verify)
        call(call)
        self.assertEqual(len(Call._current.stack), 0)
        self.assertEqual(len(Call._calls), 0)

    def test_nothing_current(self):
        self.assertTrue(Call.current() is None)

    def test_nested(self):
        preceding = Call(None)
        call = Call(self.verify)
        Call._current.stack = [preceding.id]
        Call._calls[preceding.id] = preceding
        call(call, 2)
        self.assertEqual(len(Call._current.stack), 1)
        self.assertEqual(len(Call._calls), 1)
        self.assertEqual(Call._current.stack[-1], preceding.id)
        self.assertFalse(Call._calls[preceding.id].canceled)
        Call._current.stack.pop()
        del Call._calls[preceding.id]

    def test_cancel_not_running(self):
        Call._current.stack = []
        call = Call(self.verify)
        self.assertFalse(call.canceled)
        self.assertFalse(Call.current_canceled())
        call.cancel()
        self.assertEqual(len(Call._current.stack), 0)
        self.assertEqual(len(Call._calls), 0)


class TestWithThreads(TestCase):

    def test_methods(self):
        dog_1 = Dog()
        dog_2 = Dog()
        call_1 = Call(dog_1.bark)
        call_2 = Call(dog_2.bark)
        t1 = Thread(target=call_1, args=['hello'])
        t1.start()
        t2 = Thread(target=call_2, args=['hello'])
        t2.start()
        call_1.cancel()
        t1.join()
        self.assertTrue(t2.isAlive())
        call_2.cancel()
        t2.join()

    def test_different_functions(self):
        call_1 = Call(bark)
        call_2 = Call(bark)
        t1 = Thread(target=call_1, args=['hello'])
        t1.start()
        t2 = Thread(target=call_2, args=['hello'])
        t2.start()
        call_1.cancel()
        self.assertTrue(t2.isAlive())
        t1.join()
        call_2.cancel()

    def test_nested(self):
        dog = Dog()
        bark_1 = Call(bark)
        bark_2 = Call(dog.bark)
        nested = Call(wag)
        t1 = Thread(target=bark_1, args=[wag])
        t1.start()
        t2 = Thread(target=bark_2, args=[nested])
        t2.start()
        bark_1.cancel()
        t1.join()
        self.assertTrue(t2.isAlive())
        self.assertFalse(dog.canceled)
        nested.cancel()
        t2.join(0.1)
        self.assertTrue(t2.isAlive())
        self.assertFalse(dog.canceled)
        bark_2.cancel()
        t2.join()
