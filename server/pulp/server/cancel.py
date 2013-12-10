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
"""
Facility for making synchronous function/method calls that can be
canceled.  The caller wraps the callable in a Call object which is then
invoked.  The call object can then be canceled() by another thread.
The Call class provides a sentinel to be used in loops involved in the
call flow.

Example (caller):

Thread #1:

def bar():
  while not Call.canceled():
    do_something()  # long running

def foo():
  while not Call.canceled():
    bar()

call = Call(foo)  # cancelable foo()
call()

Thread #2:

call.cancel()
"""

from threading import local, RLock

_calls = {}
_current = local()


class Call(object):
    """
    Provides wrapper for cancelable function/method invocation.
    :cvar _calls: Call cancel status: {call_id: canceled}.
    :cvar _calls: dict
    :cvar _current: Call stack in the current thread used to find
        the currently running call_id.  The call_id is contained in the
        'stack' attribute on the thread local.
    :type _current: Thread local.
    :ivar _mutex: Protected concurrent access to _calls.
    :type _mutex: RLock.
    :ivar id: The call ID.
    :type id: int
    :ivar target: The wrapped callable.
    :type target: callable
    """

    _calls = {}
    _current = local()
    _mutex = RLock()

    @staticmethod
    def canceled():
        """
        Get whether the current call has been cancelled.
        Sentinel to be used in loops.
        :return: True if canceled.
        :rtype: bool
        """
        Call._mutex.acquire()
        try:
            call_id = Call._current.stack[-1]
            return Call._calls[call_id]
        except (AttributeError, IndexError):
            return False
        finally:
            Call._mutex.release()

    def __init__(self, target):
        """
        :param target: The wrapped callable.
        :type target: callable
        """
        self.id = id(self)
        self.target = target

    def __call__(self, *args, **kwargs):
        """
        Invoke the target with the specified arguments.
         - Push call_id on the stack.
         - Set canceled (False) for this call.
         - Invoke target.
         - Pop call_id from stack.
         - Delete canceled flag.
        :param args: Arguments passed to target.
        :param kwargs: Keywords passed to target.
        :return: Whatever target() returns.
        """
        try:
            Call._current.stack.append(self.id)
        except AttributeError:
            Call._current.stack = [self.id]
        self._add()
        try:
            self.target(*args, **kwargs)
        finally:
            Call._current.stack.pop()
            self._delete()

    def _add(self):
        Call._mutex.acquire()
        try:
            Call._calls[self.id] = False
        finally:
            Call._mutex.release()

    def _delete(self):
        Call._mutex.acquire()
        try:
            del Call._calls[self.id]
        finally:
            Call._mutex.release()

    def cancel(self):
        """
        Cancel the call.
        """
        Call._mutex.acquire()
        try:
            if self.id in Call._calls:
                Call._calls[self.id] = True
        finally:
            Call._mutex.release()
