#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import functools
import logging
from pprint import pformat

import pymongo

from pulp.model import Event


_connection = pymongo.Connection()
_objdb = _connection._database.events

#_log_formatter = logging.Formatter('%(asctime)s %(messages)s')
_log_file_handler = logging.FileHandler('/var/log/pulp/events.log')
#_log_file_handler.setFormatter(_log_formatter)
_log = logging.getLogger(__name__)
_log.addHandler(_log_file_handler)
_log.setLevel(logging.DEBUG)


def audit(method):
    """
    API class instance method decorator meant to log calls that constitute
    events on pulp's model instances.
    Any call to a decorated method will both record the event in the database
    and log it to a special log file.
    
    A decorated method may have an optional keyword argument, 'principal',
    passed in that represents the user or other entity making the call.
    This optional keyword argument is *not* passed to the underlying method.
    """
    #ns_class = getattr(method, 'ns_class', None)
    #api = getattr(ns_class, '__name__', None)
    api = getattr(method, 'ns_class', None)
    method_name = method.__name__
    
    @functools.wraps(method)
    def _audit(self, *args, **kwargs):
        principal = kwargs.pop('principal', None)
        params = list(args[:])
        params.extend(kwargs.items())
        params_repr = ', '.join(pformat(p) for p in params)
        action = '%s.%s: %s' % (api, method_name, params_repr)
        event = Event(principal, action, api, method_name, params)
        _objdb.insert(event, safe=False)
        _log.info('%s called %s.%s on %s' % (principal, api, method_name, params_repr))
        return method(self, *args, **kwargs)
    
    return _audit