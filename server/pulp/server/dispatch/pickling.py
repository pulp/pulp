# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# NOTE this module is self-contained from the rest of the dispatch package as
# I'm not really sure it should live here, in the db package, or somewhere else

import copy_reg
import datetime
import types

import isodate

from pulp.common import dateutils
from pulp.server.exceptions import PulpExecutionException

# exceptions -------------------------------------------------------------------

class PicklingError(PulpExecutionException):
    pass

class UnpicklingError(PulpExecutionException):
    pass

class InstanceMethodPicklingError(PicklingError):
    pass

class InstanceMethodUnpicklingError(UnpicklingError):
    pass

# pickling support initialization ----------------------------------------------

def initialize():
    copy_reg.pickle(types.MethodType, pickle_instance_method, unpickle_instance_method)
    copy_reg.pickle(datetime.tzinfo, pickle_timezone_information, unpickle_timezone_information)

# custom pickling/unpickling functions -----------------------------------------

def pickle_instance_method(method):
    """
    Pickle object instance method
    @param method: instance method
    """
    method_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    if not issubclass(cls, object):
        raise InstanceMethodPicklingError(cls.__name__, method_name)
    return unpickle_instance_method, (method_name, obj, cls)


def unpickle_instance_method(method_name, obj, cls):
    """
    Unpickle object instance method
    @param method_name: instance method name
    @param obj: object instance
    @param cls: object class
    """
    func = None
    key = method_name
    if method_name.startswith('__'):
        key = '_' + cls.__name__ + method_name
    for c in cls.mro():
        func = c.__dict__.get(key, None)
        if func is not None:
            break
    else: # raise error if we didn't break from the loop
        InstanceMethodUnpicklingError(cls.__name__, method_name)
    return func.__get__(obj, cls)


def pickle_timezone_information(tzinfo):
    """
    Pickle timezone information
    @param tzinfo: timezone information
    """
    offset = tzinfo.utcoffset(None)
    return unpickle_timezone_information, (offset,)


def unpickle_timezone_information(offset):
    """
    Unpickle timezone information
    @param offset: timezone utc offset
    """
    utc_tz = dateutils.utc_tz()
    utc_offset = utc_tz.utcoffset(None)
    if offset == utc_offset:
        return utc_tz
    local_tz = dateutils.local_tz()
    local_offset = local_tz.utcoffset(None)
    if offset == local_offset:
        return local_tz
    offset_hours = offset.days * 24
    offset_minutes = offset.seconds / 60
    return isodate.FixedOffset(offset_hours, offset_minutes)
