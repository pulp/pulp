# -*- coding: utf-8 -*-
#
# Copyright © 2010-2012 Red Hat, Inc.
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
This module provides "backward compatibility" for both python's standard library
and third-party modules.
"""

# stdlib imports ---------------------------------------------------------------

try:
    import json as _json
except ImportError:
    import simplejson as _json

json = _json

# pymongo imports --------------------------------------------------------------

try:
    from bson import json_util as _json_util
except ImportError:
    from pymongo import json_util as _json_util

json_util = _json_util


try:
    from bson.objectid import ObjectId as _ObjectId
except ImportError:
    from pymongo.objectid import ObjectId as _ObjectId

ObjectId = _ObjectId


try:
    from bson import BSON as _BSON
except ImportError:
    from pymongo.bson import BSON as _BSON

BSON = _BSON


try:
    from bson.son import SON as _SON
except ImportError:
    from pymongo.son import SON as _SON

SON = _SON

# functools wraps decorator ----------------------------------------------------

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


