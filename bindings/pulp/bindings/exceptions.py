"""
Defines exception classes to handle server connection and request exceptions
"""

from gettext import gettext as _


class RequestException(Exception):
    """
    Base exception class for all exceptions that originate by the Pulp server. These
    exceptions coming from the server use the standard exception structure and can be parsed
    accordingly.
    """
    def __init__(self, response_body):
        Exception.__init__(self)
        self.href = response_body.pop('_href', None)
        self.http_request_method = response_body.pop('http_request_method', None)
        self.http_status = response_body.pop('http_status', None)
        self.error_message = response_body.pop('error_message', None)
        self.exception = response_body.pop('exception', None)
        self.traceback = response_body.pop('traceback', None)

        # Anything not explicitly removed above represents extra data to further
        # classify the exception.
        self.extra_data = response_body

    def __str__(self):
        message_data = {'m' : self.http_request_method,
                        'h' : self.href,
                        's' : self.http_status,
                        'g' : self.error_message}
        return _('RequestException: %(m)s request on %(h)s failed with %(s)s - %(g)s' % message_data)


# Response code = 400
class BadRequestException(RequestException): pass


# Response code = 401
class PermissionsException(RequestException): pass


# Response code = 404
class NotFoundException(RequestException): pass


# Response code = 409
class ConflictException(RequestException): pass


# Response code >= 500
class PulpServerException(RequestException): pass


# Response code >= 500 and not a Pulp formatted error
class ApacheServerException(Exception):
    """
    If Apache raises the error, it won't be in the standard Pulp format.
    Therefore this class does not subclass RequestException and simply
    stores the string returned from Apache.

    We store the response body given to us with the error, but it's an HTML
    page that basically says stuff broke, so it's not terribly useful. The
    user will still likely need to go to the server to figure out what went
    wrong.
    """

    def __init__(self, message):
        """
        @param message: the response body apache returns with the error
        @type  message: str
        """
        Exception.__init__(self)

        self.message = message


class ClientSSLException(Exception):
    """
    Raised in the event the client-side libraries refuse to communicate with the server.
    """
    pass


class ClientCertificateExpiredException(ClientSSLException):
    """
    Raised when the client certificate has expired. The
    client-side libraries will check for this before initiating the request.
    """
    def __init__(self, cert_filename):
        Exception.__init__(self)
        self.cert_filename = cert_filename


class CertificateVerificationException(ClientSSLException):
    """
    Raised when the client does not trust the authority that signed the server's SSL certificate.
    This could indicate a man-in-the-middle attack, a self-signed certificate, or a certificate
    signed by an untrusted certificate authority.
    """
    pass


class MissingCAPathException(ClientSSLException):
    """
    Raised when the bindings are given a ca_path that either doesn't exist or can't be determined to
    exist due to permissions.
    """
    pass


class ConnectionException(Exception):
    """
    Exception to indicate a less than favorable response from the server.
    The arguments are [0] the response status as an integer and
    [1] the response message as a dict, if we managed to decode from json,
    or a str if we didn't [2] potentially a traceback, if the server response
    was a python error, otherwise it will be None
    """
    pass
