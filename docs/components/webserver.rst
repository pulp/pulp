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

  If you wish to serve content over both http and https, you can use a prefix when setting
  base_paths for your Distributions to indicate whether the content will be served via http or
  https. For example, you might prefix all your distribution paths with ``/https/.../`` or
  ``/http/.../`` and then proxy your webserver's https requests to ``/pulp/content/https/`` and http
  requests to ``/pulp/content/http/``.

Plugin Views
  Plugins can contribute views anywhere in the url namespace are are not restricted to ``/pulp/``.
  Refer to your plugin documentation to understand the url needs of any given plugin. Another option
  is to route ``/``.

Using the urls above you can choose which webservers and how many will serve the different parts of
the Pulp application. If you want to have a single rule to serve all components of the Pulp web
application, routing ``/`` to it is simple and will always work.

.. _static-content:

Static Content
==============

When browsing the REST API or the browsable documentation with a web browser, for a good experience,
you'll need static content to be served.

In Development
--------------

If using the built-in Django webserver and your settings.yaml has ``DEBUG: True`` then static
content is automatically served for you.

In Production
-------------

For production environments, configure static content as follows:

1. Pick the URL static content is served at, e.g. ``/static/`` and set that as the STATIC_URL in the
settings.yaml file. Then select the path on the local filesystem where static content will be
stored, and set that as STATIC_ROOT.

2. Configure your webserver to serve the STATIC_ROOT directory's contents at the STATIC_URL url.

3. Once configured, collect all of the static content into place using the ``collectstatic`` command
as follows::

    $ pulp-manager collectstatic

For more information on scaling your static content, configuring object storage to serve your static
media, and other topics refer to the
`Django Static Media docs <https://docs.djangoproject.com/en/2.0/howto/static-files/deployment/>`_
