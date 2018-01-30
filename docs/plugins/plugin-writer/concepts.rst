Pulp Plugin Concepts
====================

The Pulp Core does not manage any content itself. This functionality is provided by
its plugins, which use the Pulp Core Plugin API to manage specific types of content,
like RPM Packages or Puppet Modules. To do this, the Pulp Core extends the Django
Web Framework and the Django REST Framework to provide a set of base classes that can be
implemented in plugins to manage content in a way that is consistent across plugins, while
still allowing plugin writers the freedom to define their workflows as they deem necessary.


.. _plugin-django-application:

Plugin Django Application
-------------------------

Like the Pulp Core itself, all Pulp Plugins begin as Django Applications, started like
any other with ``django-admin startapp <your_plugin>``. However, instead of subclassing
Django's ``django.apps.AppConfig`` as seen `in the Django documentation
<https://docs.djangoproject.com/en/1.8/ref/applications/#for-application-authors>`_,
Pulp Plugins identify themselves as plugins to the ``pulpcore`` by subclassing
:class:`pulpcore.plugin.PulpPluginAppConfig`. ``PulpPluginAppConfig``
also provides the application autoloading behaviors, such as automatic registration of
viewsets with the API router, which is necessary for Pulp plugins to create API endpoints.

For any plugin, the subclass of ``PulpPluginAppConfig`` must set its ``name`` attribute to
the importable dotted Python location of the plugin application (the Python namespace
that contains at least models and viewsets). Additionally, it should also set its ``label``
attribute to something that unambiguously labels which plugin is represented by that
subclass. See `how it is done
<https://github.com/pulp/pulp_example/blob/master/pulp_example/app/__init__.py>`_ in
``pulp_example`` plugin.


.. _plugin-entry-point:

pulpcore.plugin Entry Point
---------------------------

The Pulp Core discovers available plugins by inspecting the pulpcore.plugin entry point.

Once a plugin has defined its ``PulpPluginAppConfig`` subclass, it should add a pointer
to that subclass using the Django ``default_app_config`` convention, e.g.
``default_app_config = pulp_myplugin.app.MyPulpPluginAppConfig`` somewhere in the module
that contains your Django application. The Pulp Core can then be told to use this value
to discover your plugin, by pointing the pulpcore.plugin entry point at it. If, for example, we
set ``default_app_config`` in ``pulp_myplugin/__init__.py``, the setup.py ``entry_points``
would look like this::

    entry_points={
        'pulpcore.plugin': [
            'pulp_myplugin = pulp_myplugin:default_app_config',
        ]
    }

If you do not wish to use Django's ``default_app_config`` convention, the name given to
the ``pulpcore.plugin`` entry point must be an importable identifier with a string value
containing the importable dotted path to your plugin's application config class, just
as ``default_app_config`` does.

Check out ``pulp_example`` plugin: `default_app_config
<https://github.com/pulp/pulp_example/blob/master/pulp_example/__init__.py>`_ and `setup.py example
<https://github.com/pulp/pulp_example/blob/master/setup.py>`_.


.. _model-serializer-viewset-discovery:

Model, Serializer, Viewset Discovery
------------------------------------

The structure of plugins should, where possible, mimic the layout of the Pulp Core Plugin API.
For example, model classes should be based on platform classes imported from
:mod:`pulpcore.plugin.models` and be defined in the ``models`` module of a plugin app. ViewSets
should be imported from :mod:`pulpcore.plugin.viewsets`, and be defined in the ``viewsets`` module
of a plugin app, and so on.

This matching of module names is required for the Pulp Core to be able to auto-discover
plugin components, particularly for both models and viewsets.

Take a look at `the structure <https://github.com/pulp/pulp_example/tree/master/pulp_example/app>`_
of the ``pulp_example`` plugin.


.. _error-handling-basics:

Error Handling
--------------

Please see the :ref:`error-handling` section for details on fatal exceptions.

Non fatal exceptions should be recorded with the
:meth:`~pulpcore.plugin.tasking.Task.append_non_fatal_error` method. These non-fatal exceptions
will be returned in a :attr:`~pulpcore.app.models.Task.non_fatal_errors` attribute on the resulting
:class:`~pulpcore.app.models.Task` object.


Documenting your API
--------------------

Each instance of Pulp optionally hosts dynamically generated API documentation located at
`http://pulpserver/api/v3/docs/` if you install `drf-openapi <https://github.com/limdauto/drf_openapi/>`_.

The API endpoint description is generated from the docstring on the CRUD methods on a ViewSet.

Individual parameters and responses are documented automatically based on the Serializer field type.
A field's description is generated from the "help_text" kwarg when defining serializer fields.

Response status codes can be generated through the `Meta` class on the serializer:

.. code-block:: python

    from rest_framework.status import HTTP_400_BAD_REQUEST

    class SnippetSerializerV1(serializers.Serializer):
        title = serializers.CharField(required=False, allow_blank=True, max_length=100)

        class Meta:
            error_status_codes = {
                HTTP_400_BAD_REQUEST: 'Bad Request'
            }
