# -*- coding: utf-8 -*-
"""
This module contains a few items that we have come to love from versions of Python that are newer
than 2.4. Because we love those things so much, we have brought them into this file so that our code
can use them. Each comment block represents an item we wanted that you can import from this file.
"""
import __builtin__
import pkgutil

import backports.pkgutil


def check_builtin(module):
    """
    This decorator tries to return a function of the same name as f from the given module, and falls
    back to just returning f. This is useful for backporting builtin functions that don't exist in
    early versions of python.

    :param f:      function being decorated
    :type  f:      function
    :param module: The module that would contain f, if it exists in this implementation of Python
    :type  module: module
    :return:       builtin function if found, else f
    """
    def wrap(f):
        return getattr(module, f.__name__, f)
    return wrap


# This provides json.
try:
    import json
except ImportError:
    import simplejson as json  # noqa


# This provides the builtin, all.
@check_builtin(__builtin__)
def all(iterable):
    """
    This should behave like the builtin function "all()", which was new
    in python 2.5.
    """
    for x in iterable:
        if not x:
            return False
    return True


# This provides the builtin, any.
@check_builtin(__builtin__)
def any(iterable):
    """
    This should behave like the builtin function "any()", which is not present
    in python 2.4
    """
    for x in iterable:
        if x:
            return True
    return False


# This provides pkgutil.iter_modules.
@check_builtin(pkgutil)
def iter_modules(*args, **kwargs):
    return backports.pkgutil.iter_modules(*args, **kwargs)


try:
    import unittest2 as unittest
except ImportError:
    import unittest  # noqa
