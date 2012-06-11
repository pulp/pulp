# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import base

from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallReport, CallRequest

# call test api ----------------------------------------------------------------

class Functor(object):

    def __init__(self):
        self.args = []
        self.kwargs = {}

    def __call__(self, *args, **kwargs):
        self.args.extend(args)
        self.kwargs.update(kwargs)


class Class(object):

    def method(self, *args, **kwargs):
        pass


def function(*args, **kwargs):
    pass

# call request testing ---------------------------------------------------------

class CallRequestTests(base.PulpServerTests):

    def test__instantiation(self):
        call = Functor()
        try:
            call_request = CallRequest(call)
        except Exception, e:
            self.fail(e.message)

    def test_args(self):
        call = Functor()
        args = ['fee', 'fie', 'foe', 'foo']
        try:
            call_request = CallRequest(call, args)
        except Exception, e:
            self.fail(e.message)

    def test_kwargs(self):
        call = Functor()
        kwargs = {'one': 'foo', 'two': 'bar', 'three': 'baz'}
        try:
            call_request = CallRequest(call, kwargs=kwargs)
        except Exception, e:
            self.fail(e.message)

    def test_function_str(self):
        name = 'function'
        call_request = CallRequest(function)
        self.assertTrue(call_request.callable_name() == name)

    def test_method_str(self):
        name = 'Class.method'
        instance = Class()
        call_request = CallRequest(instance.method)
        self.assertTrue(call_request.callable_name() == name)

    def test_call_request_str(self):
        expected = "CallRequest: function('fee', 'fie', 'foe', 'foo', one='foo', three='baz', two='bar')"
        args = ['fee', 'fie', 'foe', 'foo']
        kwargs = {'one': 'foo', 'two': 'bar', 'three': 'baz'}
        call_request = CallRequest(function, args, kwargs)
        call_request_str = str(call_request)
        self.assertTrue(call_request_str == expected, '"%s" != "%s"' % (call_request_str, expected))

    def test_control_hooks(self):
        call_request = CallRequest(function)
        for key in dispatch_constants.CALL_CONTROL_HOOKS:
            self.assertTrue(call_request.control_hooks[key] is None)
        for key in dispatch_constants.CALL_CONTROL_HOOKS:
            call_request.add_control_hook(key, function)
            self.assertTrue(call_request.control_hooks[key] is function)

    def test_execution_hooks(self):
        call_request = CallRequest(function)
        for key in dispatch_constants.CALL_LIFE_CYCLE_CALLBACKS:
            self.assertTrue(isinstance(call_request.execution_hooks[key], list))
            self.assertTrue(len(call_request.execution_hooks[key]) == 0)
            call_request.add_life_cycle_callback(key, function)
            self.assertTrue(isinstance(call_request.execution_hooks[key], list))
            self.assertTrue(len(call_request.execution_hooks[key]) == 1)

    def test_serialize_deserialize(self):
        args = ['fee', 'fie', 'foe', 'foo']
        kwargs = {'one': 'foo', 'two': 'bar', 'three': 'baz'}
        call_request = CallRequest(function, args, kwargs)
        data = call_request.serialize()
        self.assertTrue(isinstance(data, dict))
        call_request_2 = CallRequest.deserialize(data)
        self.assertTrue(isinstance(call_request_2, CallRequest), str(type(call_request_2)))

    def test_serialize_deserialize_with_control_hook(self):
        key = dispatch_constants.CALL_CANCEL_CONTROL_HOOK
        call_request = CallRequest(function)
        call_request.add_control_hook(key, function)
        data = call_request.serialize()
        self.assertTrue(isinstance(data, dict))
        call_request_2 = CallRequest.deserialize(data)
        self.assertTrue(isinstance(call_request_2, CallRequest))
        self.assertTrue(call_request_2.control_hooks[key] == function)

    def test_serialize_deserialize_with_execution_hook(self):
        key = dispatch_constants.CALL_CANCEL_LIFE_CYCLE_CALLBACK
        call_request = CallRequest(function)
        call_request.add_life_cycle_callback(key, function)
        data = call_request.serialize()
        self.assertTrue(isinstance(data, dict))
        call_request_2 = CallRequest.deserialize(data)
        self.assertTrue(isinstance(call_request_2, CallRequest))
        self.assertTrue(call_request_2.execution_hooks[key][0] == function)

    def test_call_report_instantiation(self):
        try:
            call_report = CallReport()
        except Exception, e:
            self.fail(e.message)
