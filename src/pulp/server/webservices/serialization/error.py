
"""
Pulp error serialization.
"""

import copy
import httplib
import traceback

from pulp.server.webservices.serialization import link


_ERROR_OBJ_SKEL = {
    'http_status': httplib.INTERNAL_SERVER_ERROR,
    'href': None,
    'error_messege': None,
    'exception': None,
    'traceback': None,
}


def serialize_exception(e, tb=None, msg=None):
    """
    Serialize an (possibly unhandled) exception.
    @param e: exception
    @type e: Exception
    @param tb: traceback
    @type tb: traceback
    @param msg: error messege
    @type msg: str
    @return: serialized error
    @rtype: dict
    """
    error_obj = copy.copy(_ERROR_OBJ_SKEL)
    error_obj['error_messege'] = msg
    error_obj['exception'] = repr(e)
    error_obj['traceback'] = traceback.format_tb(tb)
    error_obj.update(link.current_link_obj())
    return error_obj


def serialize_http_error(http_status, msg=None):
    """
    Serialize an http error.
    @param http_status: valid http status number
    @type http_status: int
    @param msg: error messege
    @type: str
    @return: serialized error
    @rtype: dict
    """
    error_obj = copy.copy(_ERROR_OBJ_SKEL)
    error_obj['http_status'] = http_status
    error_obj['error_messege'] = msg
    error_obj.update(link.current_link_obj())
    return error_obj
