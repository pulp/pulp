.. _wsgi-application:

WSGI Application
================

Pulp is a Django based WSGI application that serves three types of URLs (aka views in Django). This
document outlines the deployment needs of the different parts of the Pulp web application.

By understanding the different parts, you can choose to deploy and scale them separately.

REST API
  The Pulp REST API is rooted at ``/pulp/api/v3/``. To serve the REST API, have a WSGI compatible
  webserver route urls matching ``/pulp/api/v3/`` to the Pulp WSGI application.

Content
  A Publication that is available via a Distribution is how Pulp serves stored content to clients
  through its web application. To serve this content,  have a WSGI compatible webserver route urls
  matching ``/pulp/content/`` to the Pulp WSGI application.

Plugin Views
  Plugins can contribute views anywhere in the url namespace are are not restricted to ``/pulp/``.
  Refer to your plugin documentation to understand the url needs of any given plugin. Another option
  is to route ``/``.

Using the urls above you can choose which webservers and how many will serve the different parts of
the Pulp application. If you want to have a single rule to serve all components of the Pulp web
application, routing ``/`` to it will is simple and will always work.
