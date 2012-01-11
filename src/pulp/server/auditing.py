# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import datetime
import inspect
import logging
import sys
import traceback
from pprint import pformat

import pymongo
try:
    from pymongo.bson import BSON
except:
    from bson import BSON
try:
    from pymongo.son import SON
except:
    from bson.son import SON

from pulp.common import dateutils
from pulp.server import async
from pulp.server import config
from pulp.server.auth.principal import get_principal
from pulp.server.api.base import BaseApi
from pulp.server.compat import wraps
from pulp.server.db.model import Event
from pulp.server.tasking.scheduler import IntervalScheduler
from pulp.server.tasking.task import Task


# globals ---------------------------------------------------------------------

# setup log - do not change this to __name__
_log = logging.getLogger('auditing')

# auditing helper api and classes ---------------------------------------------

def audit_repr(value):
    """
    Return an audit-friendly representation of a value.
    Non-ASCII chars in unicode strings are replaced with '?'.
    @type value: any
    @param value: parameter value
    @rtype: str
    @return: string representing the value
    """
    if isinstance(value, str):
        return value.decode("utf-8").encode("ascii", "replace")
    if isinstance(value, unicode):
        return value.encode("ascii", "replace")
    if not isinstance(value, (dict, BSON, SON)):
        return repr(value)
    if 'id' in value:
        return '<id: %s>' % value['id']
    elif '_id' in value:
        return '<_id: %s>' % str(value['_id'])
    return '%s instance' % str(type(value))


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

        if params is not None:
            self.params = params
        else:
            self.params = list(args)

        self.__param_to_index = dict((a, i + 1) for i, a in
                                     enumerate(args)
                                     if a in self.params)

        defaults = spec[3]
        if defaults:
            self.__param_defaults = dict((a, d) for a, d in
                                         zip(args[0 - len(defaults):], defaults)
                                         if a in self.params)
        else:
            self.__param_defaults = {}

    def api_name(self, args):
        """
        Return the api class name for the given instance method positional
        arguments.
        @type args: list
        @param args: positional arguments of an api instance method
        @rtype: str
        @return: name of api class
        """
        assert args
        api_obj = args[0]
        if not isinstance(api_obj, BaseApi):
            return 'Unknown API'
        return api_obj.__class__.__name__

    def param_values(self, args, kwargs):
        """
        Grep through passed in arguments and keyword arguments and return a list
        of values corresponding to the parameters of interest.
        @type args: list or tuple
        @param args: positional arguments
        @type kwargs: dict
        @param kwargs: keyword arguments
        @rtype: tuple of tuples
        @return: list of (paramter, value) for parameters of interest
        """
        values = []
        for p in self.params:
            i = self.__param_to_index[p]
            if i < len(args):
                values.append(audit_repr(args[i]))
            else:
                value = kwargs.get(p, self.__param_defaults.get(p, 'Unknown Parameter'))
                values.append(audit_repr(value))
        return zip(self.params, values)

# auditing decorator ----------------------------------------------------------

def audit(params=None, record_result=False):
    """
    API class instance method decorator meant to log calls that constitute
    events on pulp's model instances.
    Any call to a decorated method will both record the event in the database
    and log it to a special log file.

    @type params: list or tuple of str's or None
    @param params: list of names of parameters to record the values of,
                   None records all parameters
    @type record_result: bool
    @param record_result: whether or not to record the result
    """
    def _audit_decorator(method):

        # don't even bother to decorate the method if auditing is turned off
        if not config.config.getboolean('auditing', 'audit_events'):
            return method

        inspector = MethodInspector(method, params)

        @wraps(method)
        def _audit(*args, **kwargs):

            # convenience function for recording events
            def _record_event():
                Event.get_collection().insert(event, safe=False, check_keys=False)
                _log.info('[%s] %s called %s.%s on %s' %
                          (event.timestamp,
                           unicode(principal),
                           api,
                           inspector.method,
                           param_values_str))

            # build up the data to record
            principal = get_principal()
            api = inspector.api_name(args)
            param_values = inspector.param_values(args, kwargs)
            param_values_str = ', '.join('%s: %s' % (p, v) for p, v in param_values)
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
                if record_result:
                    event.result = audit_repr(result)
                else:
                    event.result = None
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
    @rtype: list of L{Event} instances
    @return: list of events containing fields and matching spec
    """
    assert isinstance(spec, (dict, BSON, SON)) or spec is None
    assert isinstance(fields, (list, tuple)) or fields is None
    if errors_only:
        spec = spec or {}
        spec['exception'] = {'$ne': None}
    events_ = Event.get_collection().find(spec=spec, fields=fields)
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
    @rtype: list of L{Event} instances
    @return: list of events for the given api containing fields
    """
    return events({'api': api}, fields, limit, errors_only)


def events_by_principal(principal, fields=None, limit=None, errors_only=False):
    """
    Return all recorded events for a given principal (caller).
    @type principal: model object or dict
    @param principal: principal that triggered the event (i.e. User instance)
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have
                        an exception associated with them, otherwise return all
                        events that match spec
    @rtype: list of L{Event} instances
    @return: list of events for the given principal containing fields
    """
    return events({'principal': unicode(principal)}, fields, limit, errors_only)


def events_in_datetime_range(lower_bound=None, upper_bound=None,
                             fields=None, limit=None, errors_only=False):
    """
    Return all events in a given time range.
    @type lower_bound: datetime.datetime instance or None
    @param lower_bound: lower time bound, None = oldest in db
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have
                        an exception associated with them, otherwise return all
                        events that match spec
    @rtype: list of L{Event} instances
    @return: list of events in the given time range containing fields
    """
    assert isinstance(lower_bound, datetime.datetime) or lower_bound is None
    assert isinstance(upper_bound, datetime.datetime) or upper_bound is None
    timestamp_range = {}
    if lower_bound is not None:
        timestamp_range['$gt'] = lower_bound
    if upper_bound is not None:
        timestamp_range['$lt'] = upper_bound
    if timestamp_range:
        spec = {'timestamp': timestamp_range}
    else:
        spec = None
    #spec = {'timestamp': timestamp_range} if timestamp_range else None
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
    @rtype: list of L{Event} instances
    @return: list of events in the given length of time containing fields
    """
    assert isinstance(delta, datetime.timedelta)
    now = datetime.datetime.now(dateutils.utc_tz())
    lower_bound = now - delta
    return events({'timestamp': {'$gt': lower_bound}}, fields, limit, errors_only)


def cull_events(delta):
    """
    Reaper function that removes all events older than the passed in time delta
    from the database.
    @type delta: dateteime.timedelta instance or None
    @param delta: length of time from current time to keep events,
                  None means don't keep any events
    @rtype: int
    @return: the number of events removed from the database
    """
    spec = None
    if delta is not None:
        now = datetime.datetime.now(dateutils.utc_tz())
        spec = {'timestamp': {'$lt': now - delta}}
    count = Event.get_collection().find(spec).count()
    Event.get_collection().remove(spec, safe=False)
    return count

# recurring culling of audited events -----------------------------------------

def _get_lifetime():
    """
    Get the configured auditing lifetime as a datetime.timedelta instance.
    @return: dateteime.timedelta instance
    """
    days = config.config.getint('auditing', 'lifetime')
    return datetime.timedelta(days=days)


def cull_audited_events():
    lifetime = _get_lifetime()
    cull_events(lifetime)


def init_culling_task():
    interval = datetime.timedelta(hours=12)
    tz = dateutils.local_tz()
    now = datetime.datetime.now(tz)
    if now.hour >= 13:
        now += interval
    start_time = datetime.datetime(now.year, now.month, now.day, 13, tzinfo=tz)
    scheduler = IntervalScheduler(interval, start_time)
    task = Task(cull_audited_events, scheduler=scheduler)
    async.enqueue(task)
