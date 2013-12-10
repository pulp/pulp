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

def checksum(dir_path):
  for path in list_files(dir_path):
    if not Call.current_canceled():
      checksum(path)
    else:
      break

def bar():
  for dir_path in root_directories:
    checksum(dir_path)  # long running
    if Call.current_canceled():
      break

def foo():
  for i in range(0, 100):
    if not Call.current_canceled():
      bar()
    else:
      break

call = Call(foo)  # cancelable foo()
call()

Thread #2:

call.cancel()

Benefits:
 - Easily supports canceling function call graphs.
 - Easily supports canceling instance method call graphs.
 - Easily supports canceling mixed (functions and methods) call graphs.
 - No need stored things in class attributes just to support propagating cancel.
 - Classes can be modeled without unnatural attributes such as 'canceled' flags
   or methods such as 'cancel()'.
 - Specific calls can be canceled instead of calling cancel() on objects (which is often weird).
 - To support cancel, simply add checks for Call.canceled() in loops and you're done.
"""

from threading import local


class Call(object):
    """
    Provides wrapper for cancelable function/method invocation.
    :cvar _calls: Call cancel status: {call_id: Call}.
    :cvar _calls: dict
    :cvar _current: Call stack in the current thread used to find
        the currently running call_id.  The call_id is contained in the
        'stack' attribute on the thread local.
    :type _current: Thread local.
    :ivar id: The call ID.
    :type id: int
    :ivar target: The wrapped callable.
    :type target: callable
    :ivar canceled: Canceled indicator.
    :type canceled: bool
    """

    _calls = {}
    _current = local()

    @staticmethod
    def current():
        """
        Get the current call.
        :return: The current call or None.
        :rtype: Call
        """
        try:
            call_id = Call._current.stack[-1]
            return Call._calls[call_id]
        except (AttributeError, IndexError):
            # nothing found
            pass

    @staticmethod
    def current_canceled():
        """
        Shorthand for getting whether the current call has been cancelled.
        :return: True if canceled.
        :rtype: bool
        """
        call = Call.current()
        if call is not None:
            return call.canceled
        else:
            return False

    def __init__(self, target):
        """
        :param target: The wrapped callable.
        :type target: callable
        """
        self.id = id(self)
        self.target = target
        self.canceled = False

    def __call__(self, *args, **kwargs):
        """
        Invoke the target with the specified arguments.
         - Push call_id on the stack.
         - Store the call.
         - Invoke target.
         - Pop call_id from stack.
         - Delete the call from _calls.
        :param args: Arguments passed to target.
        :param kwargs: Keywords passed to target.
        :return: Whatever target() returns.
        """
        try:
            Call._current.stack.append(self.id)
        except AttributeError:
            Call._current.stack = [self.id]
        Call._calls[self.id] = self
        try:
            self.target(*args, **kwargs)
        finally:
            Call._current.stack.pop()
            del Call._calls[self.id]

    def cancel(self):
        """
        Cancel the call.
        """
        self.canceled = True
