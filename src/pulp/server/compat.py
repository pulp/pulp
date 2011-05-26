# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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
This module provides workable substitutions for improvements made to python's 
standard library since version 2.4, while allowing pulp to run in a 2.4 
interpreter.
"""

import itertools

# functools wraps decorator ---------------------------------------------------

def _update_wrapper(orig, wrapper):
    # adopt the original's metadata
    for attr in ('__module__', '__name__', '__doc__'):
        setattr(wrapper, attr, getattr(orig, attr))
    # overwrite other attributes so our dopplegänger is complete
    for attr in ('__dict__',):
        getattr(wrapper, attr).update(getattr(orig, attr, {}))
    return wrapper

def wraps(orig):
    # decorator to make well-behaved decorators
    # http://wiki.python.org/moin/PythonDecoratorLibrary#Creating_Well-Behaved_Decorators_.2BAC8_.22Decorator_decorator.22
    def _wraps(decorator):
        return _update_wrapper(orig, decorator)
    return _wraps

# stdlib json serialization ---------------------------------------------------

import simplejson as json

# itertools.chain --------------------------------------------------------------

class chain(itertools.chain):

    @classmethod
    def from_iterable(cls, iterables):
        # chain.from_iterable(['ABC', 'DEF']) --> A B C D E F
        for it in iterables:
            for element in it:
                yield element
