"""
Centralized logic for handling the series of expected exceptions coming from
server operations (i.e. the 400 series of HTTP status codes). The handling
includes displaying consistent error messages and indicating the appropriate
exit code.

The main entry point is the handle_exception call that will detect the type of
error and handle it accordingly.

Individual handling methods are also available in the event an extension needs
to catch and display an exception using the consistent formatting but still
react to it in the extension itself.
"""

from _socket import gaierror
import logging
import os
from socket import error as socket_error
from gettext import gettext as _

from M2Crypto import X509
from M2Crypto.SSL.Checker import WrongHost

from pulp.bindings.exceptions import *
from pulp.client.arg_utils import InvalidConfig


CODE_BAD_REQUEST = os.EX_DATAERR
CODE_NOT_FOUND = os.EX_DATAERR
CODE_CONFLICT = os.EX_DATAERR
CODE_PULP_SERVER_EXCEPTION = os.EX_SOFTWARE
CODE_APACHE_SERVER_EXCEPTION = os.EX_SOFTWARE
CODE_CONNECTION_EXCEPTION = os.EX_IOERR
CODE_PERMISSIONS_EXCEPTION = os.EX_NOPERM
CODE_UNEXPECTED = os.EX_SOFTWARE
CODE_INVALID_CONFIG = os.EX_DATAERR
CODE_WRONG_HOST = os.EX_DATAERR
CODE_UNKNOWN_HOST = os.EX_CONFIG
CODE_SOCKET_ERROR = os.EX_CONFIG

_logger = logging.getLogger(__name__)


class ExceptionHandler:
    """
    Default implementation of the client-side exception middleware. Subclasses
    may override the individual handle_* methods to customize the error message
    displayed to the user, however care should be taken to return the
    appropriate exit code.
    """

    def __init__(self, prompt, config):
        """
        :param prompt: prompt instance used to display error messages
        :type  prompt: Prompt

        :param config: client configuration
        :type  config: ConfigParser
        """
        self.prompt = prompt
        self.config = config

    def handle_exception(self, e):
        """
        Analyzes the type of exception passed in and calls the appropriate
        method to handle it.

        :param e: exception raised up to the framework
        :return: exit code that describes the error
        """

        # Determine which method to call based on exception type
        mappings = (
            (BadRequestException, self.handle_bad_request),
            (NotFoundException, self.handle_not_found),
            (ConflictException, self.handle_conflict),
            (ConnectionException, self.handle_connection_error),
            (PermissionsException, self.handle_permission),
            (InvalidConfig, self.handle_invalid_config),
            (WrongHost, self.handle_wrong_host),
            (gaierror, self.handle_unknown_host),
            (socket_error, self.handle_socket_error),
            (PulpServerException, self.handle_server_error),
            (ClientCertificateExpiredException, self.handle_expired_client_cert),
            (CertificateVerificationException, self.handle_ssl_validation_error),
            (MissingCAPathException, self.handle_missing_ca_path_exception),
            (ApacheServerException, self.handle_apache_error),
        )

        handle_func = self.handle_unexpected
        for exception_type, func in mappings:
            if isinstance(e, exception_type):
                handle_func = func
                break

        exit_code = handle_func(e)
        return exit_code

    def handle_bad_request(self, e):
        """
        Handles any bad request (HTTP 400) error from the server. Based on the
        data included the error message will indicate details on what caused
        the error.

        :return: appropriate exit code for this error
        """

        self._log_server_exception(e)

        # The following keys may be present to further classify the exception:
        # property_names - values for these properties were invalid
        # missing_property_names - required properties that were not specified
        if 'property_names' in e.extra_data:
            msg = _('The values for the following properties were invalid: %(p)s')
            msg = msg % {'p': ', '.join(e.extra_data['property_names'])}
        elif 'missing_property_names' in e.extra_data:
            msg = _('The following properties are required but were not provided: %(p)s')
            msg = msg % {'p': ', '.join(e.extra_data['missing_property_names'])}
        else:
            msg = _('The server indicated one or more values were incorrect. The server '
                    'provided the following error message:')
            self.prompt.render_failure_message(msg)

            self.prompt.render_failure_message('   %s' % e.error_message)
            msg = _('More information can be found in the client log file %(l)s.')
            msg = msg % {'l': self._log_filename()}

        self.prompt.render_failure_message(msg)
        return CODE_BAD_REQUEST

    def handle_not_found(self, e):
        """
        Handles a not found (HTTP 404) error from the server.

        :return: appropriate exit code for this error
        """

        self._log_server_exception(e)

        # There are no further classifications for this error type

        msg = _('The following resource(s) could not be found:')
        self.prompt.render_failure_message(msg)

        msg = ''
        for resource_type, resource_id in e.extra_data['resources'].items():
            msg += '  %s (%s)\n' % (resource_id, resource_type)

        self.prompt.render_failure_message(msg)

        return CODE_NOT_FOUND

    def handle_conflict(self, e):
        """
        Handles a conflict on the server (HTTP 409). The cause for the 409 will
        be determined based on the included extra data and an appropriate error
        message will be displayed.

        :return: appropriate exit code for this error
        """

        self._log_server_exception(e)

        # There are two classifications for conflicts:
        # resource_id - duplicate resource
        # reasons - conflicting operation

        if 'resource_id' in e.extra_data:
            msg = _('A resource with the ID "%(i)s" already exists.')
            msg = msg % {'i': e.extra_data['resource_id']}
        elif 'reasons' in e.extra_data:
            msg = _('The requested operation conflicts with one or more operations '
                    'already queued for the resource. The following operations on the '
                    'specified resources caused the request to be rejected:\n\n')
            msg = msg

            for r in e.extra_data['reasons']:
                msg += _('Resource:  %(t)s - %(i)s\n') % {'t': r['resource_type'],
                                                          'i': r['resource_id']}
                msg += _('Operation: %(o)s') % {'o': r['operation']}
        else:
            msg = _('The requested operation could not execute due to an unexpected '
                    'conflict on the server. More information can be found in the '
                    'client log file %(l)s.')
            msg = msg % {'l': self._log_filename()}

        self.prompt.render_failure_message(msg)
        return CODE_CONFLICT

    def handle_server_error(self, e):
        """
        Handles an internal server error (HTTP 50x).

        :return: appropriate exit code for this error
        """
        self._log_server_exception(e)

        # This is a very vague error condition; the best we can do is rely on
        # the exception dump to the log file
        msg = _('An internal error occurred on the Pulp server:\n\n%(e)s')
        msg = msg % {'e': str(e)}

        self.prompt.render_failure_message(msg)
        return CODE_PULP_SERVER_EXCEPTION

    def handle_connection_error(self, e):
        """
        Handles a connection error coming out of the client's HTTP libraries.

        :return: appropriate exit code for this error
        """

        self._log_client_exception(e)

        msg = _('An error occurred attempting to contact the server. More information '
                'can be found in the client log file %(l)s.')
        msg = msg % {'l': self._log_filename()}

        self.prompt.render_failure_message(msg)
        return CODE_CONNECTION_EXCEPTION

    def handle_permission(self, e):
        """
        Handles an authentication error from the server.

        :return: appropriate exit code for this error
        """

        _logger.error(e)

        msg = _('The specified user does not have permission to execute '
                'the given command')
        self.prompt.render_failure_message(msg)

        return CODE_PERMISSIONS_EXCEPTION

    def handle_invalid_config(self, e):
        """
        Handles a client-side argument parsing exception.

        :return: appropriate exit code for this error
        """

        self._log_client_exception(e)

        self.prompt.render_failure_message(e[0])
        return CODE_INVALID_CONFIG

    def handle_wrong_host(self, e):
        """
        Handles the client connection failing because the server reported a
        different hostname in its SSL certificate than the client used to
        contact the server.

        :return: appropriate exit code for this error
        """

        self._log_client_exception(e)

        msg = _('The server hostname configured on the client did not match the '
                'name found in the server\'s SSL certificate. The client attempted '
                'to connect to [%(expected)s] but the server returned [%(actual)s] '
                'as its hostname. The expected hostname can be changed in the '
                'client configuration file.')

        data = {
            'expected': e.expectedHost,
            'actual': e.actualHost,
        }

        msg = msg % data

        self.prompt.render_failure_message(msg)
        return CODE_WRONG_HOST

    def handle_unknown_host(self, e):
        """
        Handles the client not being able to resolve the configured hostname
        for the server.

        :return: appropriate exit code for this error
        """

        self._log_client_exception(e)

        msg = _('Unable to find host [%(server)s]. Check the client '
                'configuration to ensure the server hostname is correct.')
        data = {'server': self.config['server']['host']}
        msg = msg % data

        self.prompt.render_failure_message(msg)
        return CODE_UNKNOWN_HOST

    def handle_socket_error(self, e):
        """
        Handles anything coming out of the socket layer exception handling, most notabley
        the connection refused error.

        :return: appropriate exit code for this error
        """
        self._log_client_exception(e)

        # In this exception, the first argument is an error code. Admittedly, I don't
        # know all of them. But 111 is "Connection refused", so we can handle that one
        # specifically and be generic about everything else.

        if len(e.args) > 0 and e[0] == 111:
            msg = _(
                'The connection was refused when attempting to contact the server [%(server)s]. '
                'Check the client configuration to ensure the server hostname is correct.')
            data = {'server': self.config['server']['host']}
            msg = msg % data
        else:
            msg = _('An error occurred attempting to contact the server. More information '
                    'can be found in the client log file %(l)s.')
            msg = msg % {'l': self._log_filename()}

        self.prompt.render_failure_message(msg)
        return CODE_SOCKET_ERROR

    def handle_expired_client_cert(self, e):
        """
        Handles the Exception raised when the client certificate has expired.

        :param e: The Exception that needs to be handled
        :type  e: pulp.bindings.exceptions.ClientCertificateExpiredException
        :return:  appropriate error code for this error
        :rtype:   int
        """
        msg = _('Session Expired')
        expiration_date = self._certificate_expiration_date(e.cert_filename)

        if expiration_date is not None:
            desc = _('The session certificate expired on %(e)s.')
            desc = desc % {'e': expiration_date}
        else:
            desc = _('The session certificate is expired.')

        self.prompt.render_failure_message(msg)
        self.prompt.render_paragraph(desc)

        return CODE_PERMISSIONS_EXCEPTION

    def handle_ssl_validation_error(self, e):
        """
        Handles the Exception raised when the server's certificate is not signed by a trusted
        authority.

        :param e: The Exception that was raised
        :type  e: pulp.bindings.exceptions.CertificateVerificationException
        :return:  appropriate error code for this error
        :rtype:   int
        """
        msg = _("WARNING: The server's SSL certificate is untrusted!")
        desc = _("The server's SSL certificate was not signed by a trusted authority. This could "
                 "be due to a man-in-the-middle attack, or it could be that the Pulp server needs "
                 "to have its certificate signed by a trusted authority. If you are willing to "
                 "accept the associated risks, you can set verify_ssl to False in the client "
                 "config's [server] section to disable this check.")

        self.prompt.render_failure_message(msg)
        self.prompt.render_paragraph(desc)

        return CODE_APACHE_SERVER_EXCEPTION

    def handle_missing_ca_path_exception(self, e):
        """
        This is the handler for the generic MissingCAPathException. It uses str(e) as the ca_path
        that was missing and returns os.EX_IOERR.

        :param e: The Exception that was raised
        :type  e: pulp.bindings.exceptions.MissingCAPathException
        :return:  os.EX_IOERR
        :rtype:   int
        """
        msg = _('The given CA path %(ca_path)s is not an accessible file or '
                'directory. Please ensure that ca_path exists and that your user has '
                'permission to read it.')
        msg = msg % {'ca_path': str(e)}
        self.prompt.render_failure_message(msg)
        return os.EX_IOERR

    def handle_apache_error(self, e):
        """
        Handles an exception that crops up from Apache itself, which won't have
        all of the extra data Pulp adds to its standard exception format.

        :type e: ApacheServerException
        :return: appropriate error code for this error
        """

        self._log_client_exception(e)

        msg = _('There was an internal server error while trying to '
                'access the Pulp application. One possible cause is that '
                'the database needs to be migrated to the latest version. If '
                'this is the case, run pulp-manage-db and restart the services.'
                ' More information may be found in Apache\'s log.')

        self.prompt.render_failure_message(msg)
        return CODE_APACHE_SERVER_EXCEPTION

    def handle_unexpected(self, e):
        """
        Catch-all to handle any exception that wasn't explicitly handled by
        any of the other handle_* methods in this class.

        :return: appropriate exit code for this error
        """

        self._log_client_exception(e)

        msg = _('An unexpected error has occurred. More information '
                'can be found in the client log file %(l)s.')
        msg = msg % {'l': self._log_filename()}

        self.prompt.render_failure_message(msg)
        return CODE_UNEXPECTED

    def _log_server_exception(self, e):
        """
        Dumps all information from an exception that came from the server
        to the log.

        :type e: RequestException
        """
        template = """Exception occurred:
        href:      %(h)s
        method:    %(m)s
        status:    %(s)s
        error:     %(e)s
        traceback: %(t)s
        data:      %(d)s
        """

        data = {'h': e.href,
                'm': e.http_request_method,
                's': e.http_status,
                'e': e.error_message,
                't': e.traceback,
                'd': e.extra_data}

        _logger.error(template % data)

    def _log_client_exception(self, e):
        """
        Dumps all information from a client-side originated exception to the log.

        :type e: Exception
        """
        _logger.exception('Client-side exception occurred')

    def _log_filename(self):
        """
        Syntactic sugar for reading the log filename out of the config.

        :return: full path to the log file
        """
        return self.config['logging']['filename']

    def _certificate_expiration_date(self, full_cert_path):
        """
        Attempts to read and return the expiration date of the certificate at the given
        path. If anything goes wrong, None is returned. This method should not be considered
        as any sort of validation on the certificate.

        :rtype: str or None
        """

        # This except block is pretty broad, but the intention of this method is really just to
        # help pretty up the UI by showing the expiration date if it can find it.
        try:
            f = open(full_cert_path, 'r')
            certificate = f.read()
            f.close()

            certificate_section = str(certificate[certificate.index('-----BEGIN CERTIFICATE'):])
            x509_cert = X509.load_cert_string(certificate_section)
            expiration_date = x509_cert.get_not_after()
            return str(expiration_date)
        except Exception:
            return None
