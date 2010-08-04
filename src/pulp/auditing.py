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

import datetime
import functools
import inspect
import logging
import sys
import traceback
from pprint import pformat

import pymongo
from pymongo.bson import BSON
from pymongo.son import SON

from pulp import auth
from pulp.api.base import BaseApi
from pulp.config import config
from pulp.crontab import CronTab
from pulp.model import Event

# globals ---------------------------------------------------------------------

# setup the database connection, collection, and indices
# XXX this use a centralized connection manager....
_connection = pymongo.Connection()
_objdb = _connection._database.events
_objdb.ensure_index([('id', pymongo.DESCENDING)], unique=True, background=True)
for index in ['timestamp', 'principal', 'api']:
    _objdb.ensure_index([(index, pymongo.DESCENDING)], background=True)

# setup log - do not change this to __name__
_log = logging.getLogger('auditing')

# auditing decorator ----------------------------------------------------------

class MethodInspector(object):
    """
    Class for method inspection.
    """
    def __init__(self, method, params):
        """
        @type method: unbound class instance method
        @param method: method to build spec of
        @type params: list of str's or None
        @param params: ordered list of method parameters of interest,
                       None means all parameters are of interest
        """
        assert params is None or 'self' not in params
        
        self.method = method.__name__
        
        # returns a tuple: (args, varargs, keywords, defaults)
        spec = inspect.getargspec(method)
        
        args = list(spec[0])
        # for some reason, self is sometimes in the args, and sometimes not
        if 'self' in args:
            args.remove('self')
            
        self.__param_to_index = dict((a,i+1) for i,a in
                                     enumerate(args)
                                     if params is None or a in params)
        
        self.params = params if params is not None else list(args)
            
        defaults = spec[3]
        if defaults:
            self.__param_defaults = dict((a,d) for a,d in
                                         zip(args[0-len(defaults):], defaults)
                                         if params is None or a in params)
        else:
            self.__param_defaults = {}
            
    def api_name(self, args):
        """
        Return the api class name for the given instance method positional
        arguments.
        @type args: list
        @param args: positional arguments of an api instance method
        @return: name of api class
        """
        assert args
        api_obj = args[0]
        if not isinstance(api_obj, BaseApi):
            return 'Unknown API'
        return api_obj.__class__.__name__
    
    def audit_repr(self, value):
        """
        Return an audit-friendly representation of a value.
        @type value: any
        @param value: parameter value
        @return: string representing the value
        """
        if isinstance(value, basestring):
            return value
        if not isinstance(value, (dict, BSON, SON)):
            return repr(value)
        if 'id' in value:
            return '<id: %s>' % value['id']
        elif '_id' in value:
            return '<_id: %s>' % str(value['_id'])
        return '%s instance' % str(type(value))
    
    def param_values(self, args, kwargs):
        """
        Grep through passed in arguments and keyword arguments and return a list
        of values corresponding to the parameters of interest.
        @type args: list or tuple
        @param args: positional arguments
        @type kwargs: dict
        @param kwargs: keyword arguments
        @return: list of (paramter, value) for parameters of interest
        """
        values = []
        for p in self.params:
            i = self.__param_to_index[p]
            if i < len(args):
                values.append(self.audit_repr(args[i]))
            else:
                value = kwargs.get(p, self.__param_defaults.get(p, 'Unknown Parameter'))
                values.append(self.audit_repr(value))
        return zip(self.params, values)
        

def audit(params=None, record_result=False):
    """
    API class instance method decorator meant to log calls that constitute
    events on pulp's model instances.
    Any call to a decorated method will both record the event in the database
    and log it to a special log file.
    
    A decorated method may have an optional keyword argument, 'principal',
    passed in that represents the user or other entity making the call.
    This optional keyword argument is not passed to the underlying method,
    unless the pass_principal flag is True.
    
    @type params: list or tuple of str's or None
    @param params: list of names of parameters to record the values of,
                   None records all parameters
    @type record_result: bool
    @param record_result: whether or not to record the result
    """
    def _audit_decorator(method):
        
        inspector = MethodInspector(method, params)
        
        @functools.wraps(method)
        def _audit(*args, **kwargs):
            
            # convenience function for recording events
            def _record_event():
                _objdb.insert(event, safe=False, check_keys=False)
                _log.info('[%s] %s called %s.%s on %s' %
                          (event.timestamp,
                           principal,
                           api,
                           inspector.method,
                           param_values_str))
            
            # build up the data to record
            principal = auth.get_principal()
            api = inspector.api_name(args)
            param_values = inspector.param_values(args, kwargs)
            param_values_str = ', '.join('%s: %s' % (p,v) for p,v in param_values)
            action = '%s.%s: %s' % (api,
                                    inspector.method,
                                    param_values_str)
            event = Event(principal,
                          action,
                          api,
                          inspector.method,
                          param_values)
                                
            # execute the wrapped method and record the results
            try:
                result = method(*args, **kwargs)
            except Exception, e:
                event.exception = pformat(e)
                exc = sys.exc_info()
                event.traceback = ''.join(traceback.format_exception(*exc))
                _record_event()
                raise
            else:
                event.result = inspector.audit_repr(result) if record_result else None
                _record_event()
                return result
    
        return _audit
    
    return _audit_decorator

# auditing api ----------------------------------------------------------------

def events(spec=None, fields=None, limit=None, errors_only=False):
    """
    Query function that returns events according to the pymongo spec.
    The results are sorted by timestamp into descending order.
    @type spec: dict or pymongo.son.SON instance
    @param spec: pymongo spec for filtering events
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have 
                        an exception associated with them, otherwise return all
                        events that match spec
    @return: list of events containing fields and matching spec
    """
    assert isinstance(spec, (dict, BSON, SON)) or spec is None
    assert isinstance(fields, (list, tuple)) or fields is None
    if errors_only:
        spec = spec or {}
        spec['exception'] = {'$ne': None}
    events_ = _objdb.find(spec=spec, fields=fields)
    if limit is not None:
        events_.limit(limit)
    events_.sort('timestamp', pymongo.DESCENDING)
    return list(events_)


def events_on_api(api, fields=None, limit=None, errors_only=False):
    """
    Return all recorded events for a given api.
    @type api: str
    @param api: name of the api
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have 
                        an exception associated with them, otherwise return all
                        events that match spec
    @return: list of events for the given api containing fields
    """
    return events({'api': api}, fields, limit, errors_only)


def events_by_principal(principal, fields=None, limit=None, errors_only=False):
    """
    Return all recorded events for a given principal (caller).
    @type api: model object or dict
    @param api: principal that triggered the event (i.e. User instance)
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have 
                        an exception associated with them, otherwise return all
                        events that match spec
    @return: list of events for the given principal containing fields
    """
    return events({'principal': unicode(principal)}, fields, limit, errors_only)


def events_in_datetime_range(lower_bound=None, upper_bound=None,
                             fields=None, limit=None, errors_only=False):
    """
    Return all events in a given time range.
    @type lower_bound: datetime.datetime instance or None
    @param lower_bound: lower time bound, None = oldest in db
    @type lower_bound: datetime.datetime instance or None
    @param lower_bound: upper time bound, None = newest in db
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have 
                        an exception associated with them, otherwise return all
                        events that match spec
    @return: list of events in the given time range containing fields
    """
    assert isinstance(lower_bound, datetime.datetime) or lower_bound is None
    assert isinstance(upper_bound, datetime.datetime) or upper_bound is None
    timestamp_range = {}
    if lower_bound is not None:
        timestamp_range['$gt'] = lower_bound
    if upper_bound is not None:
        timestamp_range['$lt'] = upper_bound
    spec = {'timestamp': timestamp_range} if timestamp_range else None
    return events(spec, fields, limit, errors_only)

def events_since_delta(delta, fields=None, limit=None, errors_only=False):
    """
    Return all the events that occurred in the last time delta from now.
    @type delta: datetime.timedelta instance
    @param delta: length of time frame to return events from
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have 
                        an exception associated with them, otherwise return all
                        events that match spec
    @return: list of events in the given length of time containing fields
    """
    assert isinstance(delta, datetime.timedelta)
    now = datetime.datetime.now()
    lower_bound = now - delta
    return events({'timestamp': {'$gt': lower_bound}}, fields, limit, errors_only)


def cull_events(delta):
    """
    Reaper function that removes all events older than the passed in time delta
    from the database.
    @type delta: dateteime.timedelta instance or None
    @param delta: length of time from current time to keep events,
                  None means don't keep any events
    @return: the number of events removed from the database
    """
    spec = None
    if delta is not None:
        now = datetime.datetime.now()
        spec = {'timestamp': {'$lt': now - delta}}
    count = _objdb.find(spec).count()
    _objdb.remove(spec, safe=False)
    return count

# main ------------------------------------------------------------------------

# this module is also the crontab entry script for culling entries from the
# database

def _check_crontab():
    """
    Check to see that the cull auditing events crontab entry exists, and add it
    if it doesn't.
    """
    tab = CronTab()
    cmd = 'python %s' % __file__
    if tab.find_command(cmd):
        return
    schedule = '0,30 * * * *'
    entry = tab.new(cmd, 'cull auditing events')
    entry.parse('%s %s' % (schedule, cmd))
    tab.write()
    _log.info('Added crontab entry for culling events')
    
    
def _clear_crontab():
    """
    Check to see that the cull auditing events crontab entry exists, and remove
    it if it does.
    """
    tab = CronTab()
    cmd = 'python %s' % __file__
    if not tab.find_command(cmd):
        return
    tab.remove_all(cmd)
    tab.write()
    

def _get_lifetime():
    """
    Get the configured auditing lifeteime as a datetime.timedelta instance.
    @return: dateteime.timedelta instance
    """
    days = config.getint('auditing', 'lifetime')
    return datetime.timedelta(days=days)


# check to see that a crontab entry exists on import or execution
_check_crontab()
# cull old auditing events from the database
if __name__ == '__main__':
    lifetime = _get_lifetime()
    cull_events(lifetime)