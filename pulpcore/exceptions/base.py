from gettext import gettext as _

import http.client


class PulpException(Exception):
    """
    Base exception class for Pulp.
    """
    http_status_code = http.client.INTERNAL_SERVER_ERROR

    def __init__(self, error_code):
        """
        :param error_code: unique error code
        :type error_code: str
        """
        if not isinstance(error_code, str):
            raise TypeError(_("Error code must be an instance of str."))
        self.error_code = error_code

    def __str__(self):
        """
        Returns the string representation of the exception.

        Each concrete class that inherits from :class: `pulpcore.server.exception.PulpException` is
        expected to implement it's own __str__() method. The return value is used by Pulp when
        recording the exception in the database.
        """
        raise NotImplementedError('Subclasses of PulpException must implement a __str__() method')


def exception_to_dict(exc, traceback=None):
    """
    Return a dictionary representation of an Exception.

    :param exc: Exception that is being serialized
    :type exc: Exception
    :param traceback: String representation of a traceback generated when the exception occurred.
    :type traceback: str

    :return: dictionary representing the Exception
    :rtype: dict
    """
    result = {'code': None, 'description': str(exc), 'traceback': traceback}
    if isinstance(exc, PulpException):
        result['code'] = exc.error_code
    return result


class ResourceImmutableError(PulpException):
    """
    Exceptions that are raised due to trying to update an immutable resource
    """

    def __init__(self, model):
        """
        Args:
            model (pulpcore.app.models.Model): that the user is trying to update
        """
        super().__init__("PLP0003")
        self.model = model

    def __str__(self):
        msg = _("Cannot update immutable resource {model_pk} of type {model_type}")\
            .format(resource=str(self.model.pk), type=type(self.model).__name__)
        return msg
