# -*- coding: utf-8 -*-

import logging

from django.core.urlresolvers import resolve, Resolver404

from pulp.server.webservices.http import _thread_local


_LOG = logging.getLogger(__name__)


class FrameworkRoutingMiddleware(object):
    """
    Route requests to Django if it has a matching URL, otherwise call web.py.

    Generally for more info on how WSGI is implemented in Python see [0].

    [0]: https://www.python.org/dev/peps/pep-3333/
    """

    def __init__(self, webpy_wsgi, django_wsgi):
        """
        Initializes a FrameworkRoutingMiddleware object with a webpy_wsgi and a django_wsgi stack.

        :param webpy_wsgi: A WSGI object for web.py
        :type webpy_wsgi: A WSGI compatible object
        :param django_wsgi: A WSGI object for Django
        :type django_wsgi: A WSGI compatible object
        """
        self.webpy_wsgi = webpy_wsgi
        self.django_wsgi = django_wsgi

    def __call__(self, environ, start_response):
        """
        A WSGI call that provides switching capabilities between Django and web.py.

        It supports a header named 'WebFrameworkSwitch' which can be set to 'django' or 'webpy'. It
        will check this header first and route the request accordingly.

        The default behavior is to inspect if Django supports the requested URL. If it does, the
        request is routed to Django. If it is not, it is routed to the web.py call stack.
        """
        # First check if the client is specifying the framework to use
        if 'HTTP_WEBFRAMEWORKSWITCH' in environ:
            if environ['HTTP_WEBFRAMEWORKSWITCH'] == 'django':
                return self._handle_with_django(environ, start_response)
            else:
                return self._handle_with_webpy(environ, start_response)

        # This is the start of the default behavior
        try:
            resolve(environ['PATH_INFO'], urlconf='pulp.server.webservices.urls')
        except Resolver404:
            pass
        else:
            return self._handle_with_django(environ, start_response)
        return self._handle_with_webpy(environ, start_response)

    def _handle_with_django(self, environ, start_response):
        """
        Stores the WSGI environment within thread-local data, and then have Django handle it.

        Having the wsgi_environ present in thread-local data will allow older authorization and
        authentication code written for web.py to still have access to everything it needs while
        handling a Django request which doesn't store the environment for you.
        """
        _thread_local.wsgi_environ = environ
        return self.django_wsgi(environ, start_response)

    def _handle_with_webpy(self, environ, start_response):
        """
        Removes the WSGI environment from thread-local data, and then have web.py handle it.

        Removing it ensures the older authorization and authentication code written for web.py will
        use the same code paths as before.
        """
        try:
            del _thread_local.wsgi_environ
        except AttributeError:
            pass
        return self.webpy_wsgi(environ, start_response)
