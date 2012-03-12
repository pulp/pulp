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
        super(PulpException, self).__init__(*args)
        self.message = None

    def __str__(self):
        class_name = self.__class__.__name__
        msg = '%s: %s' % (class_name, ', '.join(str(a) for a in self.args))
        return msg.encode('utf-8')

    def data_dict(self):
        return {'args': self.args}

# execution exceptions ---------------------------------------------------------

class PulpExecutionException(PulpException):
    """
    Base class of exceptions raised during the execution of Pulp.

    This should include things like bad configuration values, operation
    failures (due to networking or tasking issues), or failure to find resources
    based on the input given
    """
    pass


class InvalidConfiguration(PulpExecutionException):
    """
    Base class for exceptions raised with invalid or unsupported configuration
    values are encountered.
    """

    def __init__(self, variable, value):
        super(InvalidConfiguration, self).__init__(variable, value)
        self.variable = variable
        self.value = value

    def __str__(self):
        msg = _('Invalid configuration: %(var)s = %(val)s') % {'var': str(self.variable),
                                                               'val': str(self.value)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'variable': self.variable,
                'value': self.value}


class MissingResource(PulpExecutionException):
    """"
    Base class for exceptions raised due to requesting a resource that does not
    exist.
    """
    http_status_code = httplib.NOT_FOUND

    def __init__(self, resource_id):
        super(MissingResource, self).__init__(resource_id)
        self.resource_id = resource_id

    def __str__(self):
        msg = _('Missing resource: %(r)s') % {'r': str(self.resource_id)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'resource_id': self.resource_id}


class ConflictingOperation(PulpExecutionException):
    """
    Base class for exceptions raised when an operation cannot be completed due
    to another operation already in progress.
    """
    http_status_code = httplib.CONFLICT

    def __init__(self, reasons=None):
        super(ConflictingOperation, self).__init__(reasons)
        self.reasons = reasons

    def __str__(self):
        msg = _('Operation cannot be completed: %(r)s') % {'r': pformat(self.reasons)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'reasons': self.reasons}


class OperationFailed(PulpExecutionException):
    """
    Base class for exceptions raise when an operation fails at runtime.
    """

    def __init__(self, operation, params=(), exception=None, traceback=None):
        super(OperationFailed, self).__init__(operation, params, exception, traceback)
        self.operation = operation
        self.params = params
        self.exception = exception
        self.traceback = traceback

    def __str__(self):
        msg = _('Operation failed: %(o)s parameters=(%(p)s)') % {'o': self.operation,
                                                                 'p': ', '.join(self.params)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'operation': self.operation,
                'parameters': self.params,
                'exception': self.exception,
                'traceback': self.traceback}

# data exceptions --------------------------------------------------------------

class PulpDataException(PulpException):
    """
    Base class of exceptions raised due to data validation errors.

    This should include things like invalid, missing or superfluous data.
    """
    http_status_code = httplib.BAD_REQUEST


class InvalidType(PulpDataException):
    """
    Base class of exceptions raised due to an unknown or malformed type.
    """

    def __init__(self, invalid_type):
        super(InvalidType, self).__init__(invalid_type)
        self.invalid_type = invalid_type

    def __str__(self):
        msg = _('Invalid type: %(t)s') % {'t': str(self.invalid_type)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'invalid_type': self.invalid_type}


class InvalidValue(PulpDataException):
    """
    Base class of exceptions raised due invalid data values.
    """

    def __init__(self, variable, invalid_value):
        super(InvalidValue, invalid_value).__init__(variable, invalid_value)
        self.variable = variable
        self.invalid_value = invalid_value

    def __str__(self):
        msg = _('Invalid value for %(v)s: %(i)s') % {'v': self.variable,
                                                    'i': str(self.invalid_value)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'variable': self.variable,
                'invalid_value': self.invalid_value}


class MissingData(PulpDataException):
    """
    Base class of exceptions raised due to missing required data.
    """

    def __init__(self, *missing_variables):
        super(MissingData, self).__init__(*missing_variables)
        self.missing_variables = missing_variables

    def __str__(self):
        msg = _('Missing data for: %(v)s') % {'v': ', '.join(self.missing_variables)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'missing_variables': self.missing_variables}


class SuperfluousData(PulpDataException):
    """
    Base class of exceptions raised due to extra unknown data.
    """

    def __init__(self, *superfluous_data):
        super(SuperfluousData, self).__init__(*superfluous_data)
        self.superfluous_data = superfluous_data

    def __str__(self):
        msg = _('Superfluous data: %(s)s') % {'s': ', '.join(str(d) for d in self.superfluous_data)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'superfluous_data': self.superfluous_data}


class DuplicateResource(PulpDataException):
    """
    Bass class of exceptions raised due to duplicate resource ids.
    """
    http_status_code = httplib.CONFLICT

    def __init__(self, duplicate_id):
        super(DuplicateResource, self).__init__(duplicate_id)
        self.duplicate_id = duplicate_id

    def __str__(self):
        msg = _('Resource already exists: %(d)s') % {'d': self.duplicate_id}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'duplicate_id': self.duplicate_id}

