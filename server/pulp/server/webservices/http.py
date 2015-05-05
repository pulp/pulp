"""
HTTP utilities to help Pulp web services with HTTP using the django framework
"""

import base64
import httplib
import os
import re
import threading
import urllib

from pulp.server.compat import http_responses


_thread_local = threading.local()


API_HREF = '/pulp/api'
API_V2_HREF = API_HREF + '/v2'


def request_info(key):
    """
    Get information from the request.
    Returns the value corresponding the given key.
    Returns None if the key isn't found.
    @type key: str
    @param key: lookup key in the request information
    @rtype: str or None
    @return: request value
    """
    return _thread_local.wsgi_environ.get(key, None)


def request_method():
    """
    Get the request method for the current request.
    @return: request method
    @rtype:  str
    """
    return request_info('REQUEST_METHOD')


def request_url():
    """
    Rebuild the full request url from the request information.
    @rtype: str
    @return: full request url
    """
    scheme = request_info('wsgi.url_scheme') or 'https'
    host = request_info('HTTP_HOST') or 'localhost'
    uri = request_info('REQUEST_URI') or ''
    path = uri.split('?')[0]
    return '%s://%s%s' % (scheme, host, path)


_whitespace_regex = re.compile('\w+')


class HTTPAuthError(Exception):
    pass


def http_authorization():
    """
    Return the current http authorization credentials, if any
    @return: str representing the http authorization credentials if found,
             None otherwise
    """
    auth = request_info('HTTP_AUTHORIZATION')
    if auth is not None and auth.endswith(', Basic'):
        auth = auth[:-7]
    return auth


def _is_basic_auth(credentials):
    """
    Check if the credentials are for http basic authorization
    @type credentials: str
    @param credentials: value of the HTTP_AUTHORIZATION header
    @return: True if the credentials are for http basic authorization,
             False otherwise
    """
    if len(credentials) <= 5:
        return False
    type = credentials[:5].lower()
    return type == 'basic'


def _basic_username_password(credentials):
    """
    Get the username and password from http basic authorization credentials
    """
    credentials = credentials.strip()
    if not _whitespace_regex.match(credentials):
        raise HTTPAuthError('malformed basic authentication information')
    encoded_str = _whitespace_regex.split(credentials, 1)[1].strip()
    # All requests come in with a blank Basic authorization (for repo auth),
    # in addition to one that may be specified.  Remove the blank one.
    if encoded_str.endswith(', Basic'):
        encoded_str = encoded_str[:-7]
    decoded_str = base64.decodestring(encoded_str)
    if decoded_str.find(':') < 0:
        raise HTTPAuthError('malformed basic authentication information')
    return decoded_str.split(':', 1)


def _is_digest_auth(credentials):
    """
    Check if the credentials are for http digest authorization
    @type credentials: str
    @param credentials: value of the HTTP_AUTHORIZATION header
    @return: True if the credentials are for http digest authorization,
             False otherwise
    """
    if len(credentials) < 6:
        return False
    type = credentials[:6].lower()
    return type == 'digest'


def _digest_username_password(credentials):
    """
    Get the username and password from http digest authorization credentials
    """
    raise NotImplementedError('HTTP Digest Authorization not yet implemented')


def username_password():
    """
    Return a the username, password tuple from the http authorization header
    Return a tuple of Nones if the header isn't found
    @rtype: tuple of str's or Nones
    @return: username, password tuple
    """
    credentials = http_authorization()
    if credentials is None:
        return (None, None)
    if _is_basic_auth(credentials):
        return _basic_username_password(credentials)
    if _is_digest_auth(credentials):
        return _digest_username_password(credentials)
    return (None, None)


def ssl_client_cert():
    """
    Return the ssl client cert if it is found, None otherwise
    @rtype: str or None
    @return: pem encoded cert
    """
    return _thread_local.wsgi_environ.get('SSL_CLIENT_CERT', None)


def uri_path():
    """
    Return the current URI path
    @return: full current URI path
    """
    return unicode(_thread_local.wsgi_environ['REQUEST_URI'])


def extend_uri_path(suffix, prefix=None):
    """
    Return the current URI path with the suffix appended to it
    @param suffix:  path fragment to be appended to the current path
    @type suffix:   str
    @param prefix:  optional link prefix to use, in case the current link
                    is not what you want.
    @type prefix:   basestring
    @return: full path with the suffix appended
    """
    # steps:
    # cleanly concatenate the current path with the suffix
    # add the application prefix
    # all urls are paths, so need a trailing '/'
    # make sure the path is properly encoded
    prefix = prefix or uri_path()
    try:
        suffix = urllib.pathname2url(suffix)
    except KeyError:
        suffix = urllib.pathname2url(suffix.encode('utf-8'))
    path = os.path.normpath(os.path.join(prefix, suffix))
    return ensure_ending_slash(path)


def sub_uri_path(*args):
    """
    Return the current uri path with the last segments substituted by the
    arguments passed in.
    @param args: list of strings
    @type args: list [str, ...]
    @return: uri with args as suffix
    @rtype: str
    """
    original = uri_path()
    prefix = original.rsplit('/', len(args))[0]
    suffix = ensure_ending_slash('/'.join(args))
    url_suffix = urllib.pathname2url(suffix)
    return '/'.join((prefix, url_suffix))


def resource_path(path=None):
    """
    Return the uri path with the /pulp/api prefix stripped off
    @type path: None or str
    @param path: The uri path to convert into a resource path,
                 if the path is None, defaults to the current uri path
    @rtype: str
    @return: uri formatted path
    """
    # NOTE this function actually sucks, it makes the assumption that pulp has
    # been deployed under /pulp/api. A better way would be to grab the urls
    # from the top-level django application, but we can't do that directly as
    # it causes a circular dependency in the imports.
    if path is None:
        path = uri_path()
    parts = [p for p in path.split('/') if p]
    href_parts = API_HREF.split('/')[1:]
    while parts and parts[0] in href_parts:
        parts = parts[1:]
    if not parts:
        return '/'
    return '/%s/' % '/'.join(parts)


def ensure_ending_slash(uri_or_path):
    """
    Utility function to ensure the required ending '/' for paths in the Pulp API
    @param uri_or_path: uri or path portion of an uri
    @type uri_or_path: str
    @return: uri or path that ends with a '/'
    @rtype: str
    """
    if not uri_or_path.endswith('/'):
        uri_or_path += '/'
    return uri_or_path


