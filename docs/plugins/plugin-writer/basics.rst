Pulp Plugin Basics
==================

.. _plugin-django-application:

Plugin Django Application
-------------------------

Like the Pulp Core itself, all Pulp Plugins begin as Django Applications, started like
any other with ``django-admin startapp <your_plugin>``. However, instead of subclassing
Django's ``django.apps.AppConfig`` as seen `in the Django documentation
<https://docs.djangoproject.com/en/1.8/ref/applications/#for-application-authors>`_,
Pulp Plugins identify themselves as plugins to the Pulp Core by subclassing
:class:`pulpcore.plugin.PulpPluginAppConfig`. ``PulpPluginAppConfig``
also provides the application autoloading behaviors, such as automatic registration of
viewsets with the API router, necessary for Pulp plugins.

The ``PulpPluginAppConfig`` subclass for any plugin must set its ``name`` attribute to
the importable dotted Python location of the plugin application (the Python namespace
that contains at least models and viewsets). Additionally, it should also set its ``label``
attribute to something that unambiguously labels which plugin is represented by that
subclass. See `how it is done
<https://github.com/pulp/pulp_file/blob/master/pulp_file/app/__init__.py>`_ in
``pulp_file`` plugin.


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

Check out ``pulp_file`` plugin: `default_app_config
<https://github.com/pulp/pulp_file/blob/master/pulp_file/__init__.py>`_ and `setup.py example
<https://github.com/pulp/pulp_file/blob/master/setup.py>`_.


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

Take a look at `the structure <https://github.com/pulp/pulp_file/tree/master/pulp_file/app>`_
of the ``pulp_file`` plugin.


.. _subclassing-platform-models:

Subclassing Content, Importer, Publisher
----------------------------------------

The following classes are expected to be defined by plugin.
For more details and examples see :ref:`define-content-type`, :ref:`define-importer`, :ref:`define-publisher` sections of the guide.

Models:
 * model(s) for the specific content type(s) used in plugin, should be subclassed from Content model
 * model(s) for the plugin specific importer(s), should be subclassed from Importer model
 * model(s) for the plugin specific publisher(s), should be subclassed from Publisher model

Serializers:
 * serializer(s) for plugin specific content type(s), should be subclassed from ContentSerializer
 * serializer(s) for plugin specific importer(s), should be subclassed from ImporterSerializer
 * serializer(s) for plugin specific publisher(s), should be subclassed from PublisherSerializer

Viewsets:
 * viewset(s) for plugin specific content type(s), should be subclassed from ContentViewset
 * viewset(s) for plugin specific importer(s), should be subclassed from ImporterViewset
 * viewset(s) for plugin specific publisher(s), should be subclassed from PublisherViewset


.. _error-handling-basics:

Error Handling
--------------

Please see the :ref:`error-handling` section in the code guidelines.

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
