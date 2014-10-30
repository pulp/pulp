import httplib
from datetime import timedelta
from gettext import gettext as _
from pprint import pformat

from pulp.common import error_codes, auth_utils


class PulpException(Exception):
    """
    Base exception class for Pulp.

    Provides base class __str__ and data_dict implementations
    """
    http_status_code = httplib.INTERNAL_SERVER_ERROR

    def __init__(self, *args):
        super(PulpException, self).__init__(*args)
        self.error_code = error_codes.PLP0000
        self.error_data = {}

        # child exceptions are those that are wrapped within this exception, validation errors
        # for example would have one overall validation error and then a separate sub error
        # for each validation that failed

        self.child_exceptions = []

    def add_child_exception(self, exception):
        self.child_exceptions.append(exception)

    def to_dict(self):
        """
        The to_dict method is used to provide a standardized dictionary
        of the exception information for usage storing to the database
        or converting to json to send back via an API call
        """
        result = {
            'code': self.error_code.code,
            'description': str(self),
            'data': self.error_data,
            'sub_errors': []
        }
        for error in self.child_exceptions:
            if isinstance(error, PulpException):
                result['sub_errors'].append(error.to_dict())
            else:
                result['sub_errors'].append({'code': 'PLP0000',
                                             'description': str(error),
                                             'data': {},
                                             'sub_errors': []})
        return result

    def __str__(self):
        class_name = self.__class__.__name__
        msg = _('Pulp exception occurred: %(c)s') % {'c': class_name}
        if self.args and isinstance(self.args[0], basestring):
            msg = self.args[0]
        return msg.encode('utf-8')

    def data_dict(self):
        return {'args': self.args}


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


class PulpCodedException(PulpException):
    """
    Base class for exceptions that put the error_code and data as init arguments
    """
    def __init__(self, error_code=error_codes.PLP0001, **kwargs):
        super(PulpCodedException, self).__init__()
        self.error_code = error_code
        if kwargs:
            self.error_data = kwargs
        # Validate that the coded exception was raised with all the error_data fields that
        # are required
        for key in self.error_code.required_fields:
            if not key in self.error_data:
                raise PulpCodedException(error_codes.PLP0008, code=self.error_code.code,
                                         field=key)

    def __str__(self):
        msg = self.error_code.message % self.error_data
        return msg.encode('utf-8')


class PulpCodedValidationException(PulpCodedException):
    """
    Class for wrapping collections of coded validation errors.

    :param error_code: The particular error code that should be used for this validation exception
    :type error_code: pulp.common.error_codes.Error
    :param validation_exceptions: List of coded exceptions for each validation error that occurred
    :type validation_exceptions: list of PulpCodedException
    """

    http_status_code = httplib.BAD_REQUEST

    def __init__(self, validation_exceptions=None, error_code=error_codes.PLP1000, **kwargs):
        super(PulpCodedValidationException, self).__init__(error_code=error_code, **kwargs)
        if validation_exceptions:
            self.child_exceptions = validation_exceptions


class PulpCodedAuthenticationException(PulpCodedException):
    """
    Class for coded authentication exceptions. Raising this exception results in a
    401 Unauthorized code being returned.

    :param error_code: The particular error code that should be used for this authentication exception
    :type  error_code: pulp.common.error_codes.Error
    """

    http_status_code = httplib.UNAUTHORIZED

    def __init__(self, error_code=error_codes.PLP0025, **kwargs):
        super(PulpCodedAuthenticationException, self).__init__(error_code=error_code, **kwargs)

        # For backwards compatibility, get the old error code
        self.old_error_code = auth_utils.generate_failure_response(error_code)

    def data_dict(self):
        return self.old_error_code


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

        super(MissingResource, self).__init__(resources)
        self.error_code = error_codes.PLP0009
        self.resources = resources
        self.error_data = {'resources': resources}

    def __str__(self):
        resources_str = ', '.join('%s=%s' % (k, v) for k, v in self.resources.items())
        msg = self.error_code.message % {'resources': resources_str}
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
        super(ConflictingOperation, self).__init__(reasons)
        self.error_code = error_codes.PLP0010
        self.error_data = {'reasons': reasons}
        self.reasons = reasons

    def __str__(self):
        msg = self.error_code.message % self.error_data
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
        super(OperationTimedOut, self).__init__(timeout)
        self.error_code = error_codes.PLP0011
        self.error_data = {'timeout': timeout}
        self.timeout = timeout

    def __str__(self):
        msg = self.error_code.message % self.error_data
        return msg.encode('utf-8')

    def data_dict(self):
        return {'timeout': self.timeout}


class NoWorkers(PulpExecutionException):
    """
    This Exception is raised when there are no Celery workers available to perform asynchronous
    tasks.
    """
    http_status_code = httplib.SERVICE_UNAVAILABLE

    def __init__(self):
        """
        Initialize the NoWorkers Exception by setting its error code and message.
        """
        super(NoWorkers, self).__init__()
        self.error_code = error_codes.PLP0024

    def __str__(self):
        """
        Return a string representation of self.

        :return: str of self
        :rtype:  str
        """
        msg = self.error_code.message
        return msg.encode('utf-8')

    def data_dict(self):
        """
        Return an empty dictionary, as there is no data for this error.

        :return: empty dictionary
        :rtype:  dict
        """
        return {}


class OperationPostponed(PulpExecutionException):
    """
    Base class for handling operations postponed by the coordinator.
    """
    http_status_code = httplib.ACCEPTED

    def __init__(self, call_report):
        """
        @param call_report:  call report for postponed operation
        @type  call_report: CallReport or pulp.server.async.task.TaskResult
        """
        super(OperationPostponed, self).__init__(call_report)
        self.error_code = error_codes.PLP0012
        self.call_report = call_report
        self.error_data = {'call_report': call_report}

    def __str__(self):
        msg = self.error_code.message % self.error_data
        return msg.encode('utf-8')

    def data_dict(self):
        return {'call_report': self.call_report}


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
        super(NotImplemented, self).__init__(operation_name)
        self.operation_name = operation_name
        self.error_code = error_codes.PLP0013
        self.error_data = {'operation_name': operation_name}

    def __str__(self):
        msg = self.error_code.message % self.error_data
        return msg.encode('utf-8')

    def data_dict(self):
        return {'operation_name': self.operation_name}


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
                               if a single property_name is passed, it is converted to a list
        @type  property_names: list
        """
        super(InvalidValue, self).__init__(property_names)
        if not isinstance(property_names, (list, tuple)):
            property_names = [property_names]

        self.error_code = error_codes.PLP0015
        self.error_data = {'property_names': property_names,
                           'properties': pformat(property_names)}

        self.property_names = property_names

    def __str__(self):
        msg = self.error_code.message % self.error_data
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
        super(MissingValue, self).__init__(property_names)
        if not isinstance(property_names, (list, tuple)):
            property_names = [property_names]
        self.error_code = error_codes.PLP0016
        self.error_data = {'property_names': property_names,
                           'properties': pformat(property_names)}
        self.property_names = property_names

    def __str__(self):
        msg = self.error_code.message % self.error_data
        return msg.encode('utf-8')

    def data_dict(self):
        return {'missing_property_names': self.property_names}


class UnsupportedValue(PulpDataException):
    """
    Base class of exceptions raised due to unsupported data. The names of all
    the properties that are unsupported are specified in the constructor.
    """

    def __init__(self, property_names):
        super(UnsupportedValue, self).__init__(property_names)
        if not isinstance(property_names, (list, tuple)):
            property_names = [property_names]

        self.error_code = error_codes.PLP0017
        self.error_data = {'property_names': property_names,
                           'properties': pformat(property_names)}

        self.property_names = property_names

    def __str__(self):
        msg = self.error_code.message % self.error_data
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
        super(DuplicateResource, self).__init__(resource_id)
        self.error_code = error_codes.PLP0018
        self.error_data = {'resource_id': resource_id}
        self.resource_id = resource_id

    def __str__(self):
        msg = self.error_code.message % self.error_data
        return msg.encode('utf-8')

    def data_dict(self):
        return {'resource_id': self.resource_id}


class InputEncodingError(PulpDataException):
    """
    Error raised when input strings are not encoded in utf-8
    """

    def __init__(self, value):
        super(DuplicateResource, self).__init__(value)
        self.error_code = error_codes.PLP0019
        self.error_data = {'value': value}
        self.value = value

    def __str__(self):
        return self.error_code.message % self.error_data

    def data_dict(self):
        return {'value': self.value}


class PulpCodedTaskException(PulpCodedException):
    """
    Base class for exceptions that put the error_code and data as init arguments
    """
    def __init__(self, error_code=error_codes.PLP1000, **kwargs):
        super(PulpCodedTaskException, self).__init__(error_code=error_code, **kwargs)


class PulpCodedTaskFailedException(PulpCodedException):
    """
    Class for wrapping collections of coded task errors.

    :param error_code: The particular error code that should be used for this validation exception
    :type error_code: pulp.common.error_codes.Error
    :param task_exceptions: List of coded exceptions for each validation error that occurred
    :type task_exceptions: list of PulpCodedException
    """
