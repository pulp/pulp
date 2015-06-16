# -*- coding: utf-8 -*-
"""
This module provides "backward compatibility" for both python's standard library
and third-party modules.
"""

import sys

if sys.version_info < (2, 5):
    import sha as digestmod
else:
    from hashlib import sha256 as digestmod  # noqa
try:
    import json
except ImportError:
    import simplejson as json  # noqa


try:
    from bson import BSON
except ImportError:
    from pymongo.bson import BSON  # noqa
try:
    from bson import json_util
except ImportError:
    from pymongo import json_util  # noqa
try:
    from bson.objectid import ObjectId
except ImportError:
    from pymongo.objectid import ObjectId  # noqa
try:
    from bson.son import SON
except ImportError:
    from pymongo.son import SON  # noqa


def _update_wrapper(orig, wrapper):
    # adopt the original's metadata
    for attr in ('__module__', '__name__', '__doc__'):
        setattr(wrapper, attr, getattr(orig, attr))
    # overwrite other attributes so our dopplegänger is complete
    for attr in ('__dict__',):
        getattr(wrapper, attr).update(getattr(orig, attr, {}))
    return wrapper


def wraps(orig):
    # decorator to make well-behaved decorators. See "Creating Well-Behaved Decorators at
    # http://wiki.python.org/moin/PythonDecoratorLibrary
    def _wraps(decorator):
        return _update_wrapper(orig, decorator)
    return _wraps


http_responses = {
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    100: 'Continue',
    101: 'Switching Protocols',
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    306: '(Unused)',
    307: 'Temporary Redirect',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported'}
