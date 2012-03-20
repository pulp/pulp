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

    def __init__(self, resource_id):
        """
        @param resource_id: ID of the requested resource that was missing
        @type  resource_id: str
        """
        PulpExecutionException.__init__(self, resource_id)
        self.resource_id = resource_id

    def __str__(self):
        msg = _('Missing resource: %(r)s') % {'r': self.resource_id}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'resource_id': self.resource_id}


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


# data exceptions --------------------------------------------------------------

class PulpDataException(PulpException):
    """
    Base class of exceptions raised due to data validation errors.

    This should include things like invalid, missing or superfluous data.
    """
    # NOTE intermediate exception class, no overrides will be provided
    http_status_code = httplib.BAD_REQUEST


class InvalidType(PulpDataException):
    """
    Base class of exceptions raised due to an unknown or malformed type.
    """

    def __init__(self, invalid_type):
        """
        @param invalid_type: name of the requested but unfound type
        @type  invalid_type: str
        """
        PulpDataException.__init__(self, invalid_type)
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

    def __init__(self, invalid_value):
        """
        @param invalid_value: user
        """
        PulpDataException.__init__(self, invalid_value)
        self.invalid_value = invalid_value

    def __str__(self):
        msg = _('Invalid value: %(v)s') % {'v': pformat(self.invalid_value)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'invalid_value': self.invalid_value}


class MissingData(PulpDataException):
    """
    Base class of exceptions raised due to missing required data.
    """

    def __init__(self, data):
        PulpDataException.__init__(self, data)
        self.data = data

    def __str__(self):
        msg = _('Missing data: %(d)s') % {'d': pformat(self.data)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'missing_data': self.data}


class SuperfluousData(PulpDataException):
    """
    Base class of exceptions raised due to extra unknown data.
    """

    def __init__(self, data):
        PulpDataException.__init__(self, data)
        self.data = data

    def __str__(self):
        msg = _('Superfluous data: %(d)s') % {'d': pformat(self.data)}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'superfluous_data': self.data}


class DuplicateResource(PulpDataException):
    """
    Bass class of exceptions raised due to duplicate resource ids.
    """
    http_status_code = httplib.CONFLICT

    def __init__(self, resource_id):
        PulpDataException.__init__(self, resource_id)
        self.resource_id = resource_id

    def __str__(self):
        msg = _('Duplicate resource: %(r)s') % {'r': self.resource_id}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'resource_id': self.resource_id}

