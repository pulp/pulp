import httplib
import logging
import sys
import traceback
from gettext import gettext as _

from django.http import HttpResponse, HttpResponseServerError

from pulp.server.compat import json
from pulp.server.exceptions import PulpException
from pulp.server.webservices.views.serializers import error


logger = logging.getLogger(__name__)


class ExceptionHandlerMiddleware(object):
    """
    Catch unhandled exceptions and return appropriate 500 responses.
    """

    def process_exception(self, request, exception):
        """
        Process the catched exception.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param exception: unhandled exception
        :type exception: Exception

        :return: Response containing processed exception
        :rtype: django.http.HttpResponseServerError
        """

        if isinstance(exception, PulpException):
            status = exception.http_status_code
            response = error.http_error_obj(status, str(exception))
            response.update(exception.data_dict())
            response['error'] = exception.to_dict()
            logger.info(str(exception))
            response_obj = HttpResponse(json.dumps(response), status=status,
                                        content_type="application/json; charset=utf-8")
        else:
            status = httplib.INTERNAL_SERVER_ERROR
            response = error.http_error_obj(status, str(exception))
            msg = _('Unhandled Exception')
            logger.error(msg)

        if status == httplib.INTERNAL_SERVER_ERROR:
            logger.exception(str(exception))
            e_type, e_value, trace = sys.exc_info()
            response['exception'] = traceback.format_exception_only(e_type, e_value)
            response['traceback'] = traceback.format_tb(trace)
            response_obj = HttpResponseServerError(json.dumps(response),
                                                   content_type="application/json; charset=utf-8")
        else:
            logger.info(str(exception))

        return response_obj
