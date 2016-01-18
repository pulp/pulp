from datetime import datetime
from functools import wraps

import functools
import httplib
import json
import sys

from django.http import HttpResponse
from django.utils.encoding import iri_to_uri

from pulp.common import dateutils, error_codes
from pulp.common.util import decode_unicode, encode_unicode
from pulp.server.compat import json_util
from pulp.server.exceptions import PulpCodedValidationException, InputEncodingError


def pulp_json_encoder(obj):
    """
    Specialized json encoding.
    :param obj: An object to be encoded.

    :return: The encoded object.
    :rtype: str
    """

    if isinstance(obj, datetime):
        dt = obj.replace(tzinfo=dateutils.utc_tz())
        return dateutils.format_iso8601_datetime(dt)
    return json_util.default(obj)


def generate_json_response(content=None, response_class=HttpResponse, default=None,
                           content_type='application/json; charset=utf-8'):
    """
    Serialize an object and return a djagno response

    :param content        : content to be serialized
    :type  content        : anything that is serializable by json.dumps
    :param response_class : Django response ojbect
    :type  response_class : HttpResponse class or subclass
    :param default        : function used by json.dumps to serialize content (also called default)
    :type  default        : function or None
    :param content_type   : type of returned content
    :type  content_type   : str

    :raises               : TypeError if response does not implement Django response object API
    :return               : response containing the serialized content
    :rtype                : HttpResponse or subclass
    """

    json_obj = json.dumps(content, default=default)
    return response_class(json_obj, content_type=content_type)


"""
Shortcut function to generate a json response using the in house json_encoder.

This function is equivalent to:
generate_json_response(content, default=pulp_json_encoder)
"""
generate_json_response_with_pulp_encoder = functools.partial(
    generate_json_response,
    default=pulp_json_encoder,
)


def generate_redirect_response(response, href):
    response['Location'] = iri_to_uri(href)
    response.status_code = httplib.CREATED
    response.reason_phrase = 'CREATED'
    return response


def _ensure_input_encoding(input):
    """
    Recursively traverse any input structures and ensure any strings are
    encoded as utf-8.

    :param input: input data

    :return: input data with strings encoded as utf-8
    """

    if isinstance(input, (list, set, tuple)):
        return [_ensure_input_encoding(i) for i in input]
    if isinstance(input, dict):
        return dict((_ensure_input_encoding(k), _ensure_input_encoding(v))
                    for k, v in input.items())
    try:
        return encode_unicode(decode_unicode(input))
    except (UnicodeDecodeError, UnicodeEncodeError):
        raise InputEncodingError(input), None, sys.exc_info()[2]


def parse_json_body(allow_empty=False, json_type=None):
    """
    Ensure request body carries valid JSON of specified data type

    :param allow_empty: if True, allows request body to be empty, defaults to False.
    :type  allow_empty: bool
    :param json_type: required type of request body. If None, any type is allowed,
                      defaults to None.
    :type  json_type: type

    :raises PulpCodedValidationException: if request body contains invalid JSON or
                                          of incorrect data type.

    :return: decorator with proper parameters applied.
    :rtype: function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = args[1]
            if allow_empty and not request.body:
                request.body_as_json = {}
                return func(*args, **kwargs)
            try:
                request_json = json.loads(request.body)
            except ValueError:
                raise PulpCodedValidationException(error_code=error_codes.PLP1009)
            else:
                if not (json_type is None or isinstance(request_json, json_type)):
                    raise PulpCodedValidationException(
                        error_code=error_codes.PLP1015,
                        data_type=json_type.__name__
                    )
                request.body_as_json = _ensure_input_encoding(request_json)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def page_not_found(request, *args, **kwargs):
    """
    Returns a HttpResponse with an empty json payload and a httplib.NOT_FOUND response code.

    This function uses *args and **kwargs to be compatible with newer versions of Django which
    have additional parameters.

    :param request: The WSGI object containing the request
    :type request: django.core.handlers.wsgi.WSGIRequest
    :param args: Additional positional arguments
    :type args: list
    :param kwargs: Additional keyword arguments
    :type kwargs: dict

    :return: A response object that contains a httplib.NOT_FOUND status code and an empty json
             payload.
    :rtype: django.http.HttpResponse
    """
    json_response = generate_json_response()
    json_response.status_code = httplib.NOT_FOUND
    return json_response
