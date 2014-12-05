# -*- coding: utf-8 -*-

import logging

from django.core.urlresolvers import resolve, Resolver404

_LOG = logging.getLogger(__name__)


class FrameworkRoutingMiddleware(object):
    """
    Route requests to Django if it has a matching URL, otherwise call webPy.
    """

    def __init__(self, webpy_wsgi, django_wsgi):
        self.webpy_wsgi = webpy_wsgi
        self.django_wsgi = django_wsgi

    def __call__(self, environ, start_response):
        """
        A WSGI call that provides switching capabilities between Django and WebPy.

        It supports a header named 'WebFrameworkSwitch' which can be set to 'django' or 'webpy'. It
        will check this header first and route the request accordingly.

        The defualt behavior is to inspect if Django supports the requested URL. If it does, the
        request is routed to Django. If it is not, it is routed to the web.py call stack.
        """
        # First check if the client is specifying the framework to use
        if 'HTTP_WEBFRAMEWORKSWITCH' in environ:
            if environ['HTTP_WEBFRAMEWORKSWITCH'] == 'django':
                return self.django_wsgi(environ, start_response)
            else:
                return self.webpy_wsgi(environ, start_response)

        # This is the start of the defualt behavior
        try:
            resolve(environ['PATH_INFO'], urlconf='pulp.server.webservices.urls')
        except Resolver404:
            pass
        else:
            return self.django_wsgi(environ, start_response)
        return self.webpy_wsgi(environ, start_response)
