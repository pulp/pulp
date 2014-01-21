# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

from mock import Mock

from pulp.common import util


class TestPartial(unittest.TestCase):

    def test_no_arguments(self):
        base_func = Mock()
        wrapped_func = util.partial(base_func)

        wrapped_func()
        base_func.assert_called_once_with()

    def test_base_arguments_only(self):
        base_func = Mock()
        args = ['foo', 'bar']
        kwargs = {'baz': 'qux'}
        wrapped_func = util.partial(base_func, *args, **kwargs)

        wrapped_func()
        base_func.assert_called_once_with(*args, **kwargs)

    def test_additional_args(self):
        base_func = Mock()
        args = ['foo', 'bar']
        kwargs = {'baz': 'qux'}
        wrapped_func = util.partial(base_func, *args, **kwargs)

        additional_args = ['alpha', 'bravo']
        additional_kwargs = {'charlie': 'delta'}
        wrapped_func(*additional_args, **additional_kwargs)

        result_args = args + additional_args
        result_kwargs = {}
        result_kwargs.update(kwargs)
        result_kwargs.update(additional_kwargs)
        base_func.assert_called_once_with(*result_args, **result_kwargs)
