#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
HTTP utilities to help pulp web services with HTTP using the web.py framework
"""

import httplib
import os
import urllib

import web

# request methods -------------------------------------------------------------
    
def query_parameters(valid):
    """
    @type valid: list of str's
    @param valid: list of expected query parameters
    @return: dict of param: [value(s)] of uri query parameters
    """
    # NOTE If a keyword argument of foo=[] is not passed into web.input,
    # web.py will not record multiple parameters of 'foo' from the URI.
    # So this line of code constructs those keyword arguments for 'valid'
    # (ie expected) query parameters.
    # This will return a list for every valid parameter, even if it's empty or
    # only contains one element
    defaults = {}.fromkeys(valid, [])
    params = web.input(**defaults)
    # scrub out invalid keys and empty lists from the parameters
    return dict((k,v) for k,v in params.items() if k in valid and v)


def http_authorization():
    """
    Return the current http authorization credentials, if any
    @return: str representing the http authorization credentials if found,
             None otherwise
    """
    credentials = web.ctx.environ.get('HTTP_AUTHORIZATION', None)
    return credentials
     
# uri path functions ----------------------------------------------------------
   
def uri_path():
    """
    Return the current URI path
    @return: full current URI path
    """
    return web.http.url(web.ctx.path)


def extend_uri_path(suffix):
    """
    Return the current URI path with the suffix appended to it
    @type suffix: str
    @param suffix: path fragment to be appended to the current path
    @return: full path with the suffix appended
    """
    # steps:
    # cleanly concatenate the current path with the suffix
    # add the application prefix
    # all urls are paths, so need a trailing '/'
    # make sure the path is properly encoded
    prefix = uri_path()
    suffix = urllib.pathname2url(suffix)
    path = os.path.normpath(os.path.join(prefix, suffix))
    if not path.endswith('/'):
        path += '/'
    return path

# response functions ----------------------------------------------------------
   
def header(hdr, value, unique=True):
    """
    Adds 'hdr: value' to the response.
    This function has, in some regards, the opposite semantics of the web.header
    function. If unique is True, the hdr will be overwritten if it already
    exists in the response. Otherwise it will be appended.
    @type hdr: str
    @param hdr: valid http header key
    @type value: str
    @param value: valid value for corresponding header key
    @type unique: bool
    @param unique: whether only one instance of the header is in the response
    """
    hdr = web.utf8(hdr)
    value = web.utf8(value)
    previous = []
    for h,v in web.ctx.headers:
        if h.lower() == hdr.lower():
            previous.append((h,v))
    if unique:
        for p in previous:
            web.ctx.headers.remove(p)
    web.ctx.headers.append((hdr, value))

# status functions ------------------------------------------------------------
      
def _status(code):
    """
    Non-public function to set the web ctx status
    @type code: int
    @param code: http response code
    """
    web.ctx.status = '%d %s' % (code, httplib.responses[code])
    
    
def status_ok():
    """
    Set response code to ok
    """
    _status(httplib.OK)
    
    
def status_created():
    """
    Set response code to created
    """
    _status(httplib.CREATED)
    

def status_accepted():
    """
    Set response code to accepted
    """
    _status(httplib.ACCEPTED)
    
    
def status_bad_request():
    """
    Set the response code to bad request
    """
    _status(httplib.BAD_REQUEST)
    

def status_unauthorized():
    """
    Set response code to unauthorized
    """
    _status(httplib.UNAUTHORIZED)
    
    
def status_not_found():
    """
    Set response code to not found
    """
    _status(httplib.NOT_FOUND)
    
    
def status_method_not_allowed():
    """
    Set response code to method not allowed
    """
    _status(httplib.METHOD_NOT_ALLOWED)
    
    
def status_not_acceptable():
    """
    Set response code to not acceptable
    """
    _status(httplib.NOT_ACCEPTABLE)
    
    
def status_conflict():
    """
    Set response code to conflict
    """
    _status(httplib.CONFLICT)
    
def status_internal_server_error():
    """
    Set the resonse code to internal server error
    """
    _status(httplib.INTERNAL_SERVER_ERROR)
    