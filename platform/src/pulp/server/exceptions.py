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

import httplib
from datetime import timedelta
from gettext import gettext as _
from pprint import pformat

# base exception class ---------------------------------------------------------

class PulpException(Exception):
    """
    Base exception class for Pulp.

    Provides base class __str__ and data_dict implementations
    """
    http_status_code = httplib.INTERNAL_SERVER_ERROR

    def __init__(self, *args):
        Exception.__init__(self, *args)
        self.message = None

    def __str__(self):
        class_name = self.__class__.__name__
        msg = _('Pulp exception occurred: %(c)s') % {'c': class_name}
        if self.args and isinstance(self.args[0], basestring):
            msg = self.args[0]
        return msg.encode('utf-8')

    def data_dict(self):
        return {'args': self.args}

# execution exceptions ---------------------------------------------------------

class PulpExecutionException(PulpException):
    """
    Base class of exceptions raised during the execution of Pulp.

    This class should be used as a graceful server-side error while running
    an operation. It is acceptable to instantiate and use this class directly.

    Subclasses to this exception can be used to further describe any problems
    encountered by the server.
    """
    # NOTE intermediate exception class, no overrides will be provided
    pass


class MissingResource(PulpExecutionException):
    """"
    Base class for exceptions raised due to requesting a resource that does not
    exist.
    """
    http_status_code = httplib.NOT_FOUND

    def __init__(self, *args, **resources):
        """
        @param args: backward compatibility for for positional resource_id argument
        @param resources: keyword arguments of resource_type=resource_id
        """
        # backward compatibility for for previous 'resource_id' positional argument
        if args:
            resources['resource_id'] = args[0]
        PulpExecutionException.__init__(self, resources)
        self.resources = resources

    def __str__(self):
        resources_str = ', '.join('%s=%s' % (k, v) for k, v in self.resources.items())
        msg = _('Missing resource(s): %(r)s') % {'r': resources_str}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'resources': self.resources}


class ConflictingOperation(PulpExecutionException):
    """
    Base class for exceptions raised when an operation cannot be completed due
    to another operation already in progress.
    """
    http_status_code = httplib.CONFLICT

    def __init__(self, reasons):
        """
        @param reasons: list of dicts describing why the requested operation was denied;
               this is retrieved from the call report instance that indicated the conflict
        @type  reasons: list
        """
        PulpExecutionException.__init__(self, reasons)
        self.reasons = reasons

    def __str__(self):
        msg = _('Conflicting operation reasons: %(r)s') % {'r': self.reasons}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'reasons': self.reasons}


class OperationTimedOut(PulpExecutionException):
    """
    Base class for exceptions raised when an operation cannot be completed
    because it failed to start before a predetermined amount of time had passed.
    """
    http_status_code = httplib.SERVICE_UNAVAILABLE

    def __init__(self, timeout):
        """
        @param timeout: the timeout that expired
        @type  timeout: datetime.timedelta or str
        """
        if isinstance(timeout, timedelta):
            timeout = str(timeout)
        PulpExecutionException.__init__(self, timeout)
        self.timeout = timeout

    def __str__(self):
        msg = _('Operation timed out after: %(t)s') % {'t': self.timeout}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'timeout': self.timeout}


class OperationPostponed(PulpExecutionException):
    """
    Base class for handling operations postponed by the coordinator.
    """
    http_status_code = httplib.ACCEPTED

    def __init__(self, call_report):
        """
        @param call_report:  call report for postponed operation
        @type  call_report: CallReport
        """
        PulpExecutionException.__init__(self, call_report)
        self.call_report = call_report

    def __str__(self):
        msg = _('Operation postponed')
        return msg.encode('utf-8')

    def data_dict(self):
        return {'call_report': self.call_report}


class MultipleOperationsPostponed(PulpExecutionException):
    """
    Base class for handling multiple simultaneous asynchronous operations being
    executed by the coordinator.
    """
    http_status_code = httplib.ACCEPTED

    def __init__(self, call_report_list):
        """
        @param call_report_list: list of call reports, one for each operation
        @type call_report_list: list
        """
        PulpExecutionException.__init__(self, call_report_list)
        self.call_report_list = call_report_list

    def __str__(self):
        msg = _('Multiple Operations')
        return msg.encode('utf-8')

    def data_dict(self):
        return {'call_report_list': self.call_report_list}


class NotImplemented(PulpExecutionException):
    """
    Base class for exceptions raised in place-holders for future functionality
    or for missing control hooks in asynchronous operations, like 'cancel'.
    """
    http_status_code = httplib.NOT_IMPLEMENTED

    def __init__(self, operation_name):
        """
        @param operation_name: the name of the operation that is not implemented
        @type  operation_name: str
        """
        PulpExecutionException.__init__(self, operation_name)
        self.operation_name = operation_name

    def __str__(self):
        msg = _('Operation not implemented: %(o)s') % {'o': self.operation_name}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'operation_name': self.operation_name}

# data exceptions --------------------------------------------------------------

class PulpDataException(PulpException):
    """
    Base class of exceptions raised due to data validation errors.
    """
    # NOTE intermediate exception class, no overrides will be provided
    http_status_code = httplib.BAD_REQUEST


class InvalidValue(PulpDataException):
    """
    Base class of exceptions raised due invalid data values. The names of all
    properties that were invalid are specified in the constructor.
    """

    def __init__(self, property_names):
        """
        @param property_names: list of all properties that were invalid
        @type  property_names: list
        """
        PulpDataException.__init__(self, property_names)

        if not isinstance(property_names, (list, tuple)):
            property_names = [property_names]
        self.property_names = property_names

    def __str__(self):
        msg = _('Invalid properties: %(p)s') % {'p': pformat(self.property_names)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'property_names': self.property_names}


class MissingValue(PulpDataException):
    """
    Base class of exceptions raised due to missing required data. The names of
    all properties that are missing are specified in the constructor.
    """

    def __init__(self, property_names):
        """
        @param property_names: list of all properties that were missing
        @type  property_names: list
        """
        PulpDataException.__init__(self, property_names)

        if not isinstance(property_names, (list, tuple)):
            property_names = [property_names]
        self.property_names = property_names

    def __str__(self):
        msg = _('Missing values for: %(v)s') % {'v': pformat(self.property_names)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'missing_property_names': self.property_names}


class UnsupportedValue(PulpDataException):
    """
    Base class of exceptions raised due to unsupported data. The names of all
    the properties that are unsupported are specified in the constructor.
    """

    def __init__(self, property_names):
        PulpDataException.__init__(self, property_names)

        if not isinstance(property_names, (list, tuple)):
            property_names = [property_names]
        self.property_names = property_names

    def __str__(self):
        msg = _('Unsupported properties: %(v)s') % {'v': pformat(self.property_names)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'unsupported_property_names': self.property_names}


class DuplicateResource(PulpDataException):
    """
    Bass class of exceptions raised due to duplicate resource ids.
    """
    http_status_code = httplib.CONFLICT

    def __init__(self, resource_id):
        """
        @param resource_id: ID of the resource that was duplicated
        @type  resource_id: str
        """
        PulpDataException.__init__(self, resource_id)
        self.resource_id = resource_id

    def __str__(self):
        msg = _('Duplicate resource: %(r)s') % {'r': self.resource_id}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'resource_id': self.resource_id}

