import http.client

from pulp.common import error_codes


class PulpException(Exception):
    """
    Base exception class for Pulp.

    Provides base class __str__ and data_dict implementations
    """
    http_status_code = http.client.INTERNAL_SERVER_ERROR

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
            if key not in self.error_data:
                raise PulpCodedException(error_codes.PLP0008, code=self.error_code.code,
                                         field=key)

    def __str__(self):
        msg = self.error_code.message % self.error_data
        return msg.encode('utf-8')


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
