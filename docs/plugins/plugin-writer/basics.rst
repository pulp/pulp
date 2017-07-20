Pulp Plugin Basics
==================

.. warning::

    All the content below is here due to refactor of initial 3.0 docs
    and should be revisited for correctness.    


Plugin Django Application
-------------------------

Like the Pulp Platform itself, all Pulp Plugins begin as Django Applications, started like
any other with ``django-admin startapp <your_plugin>``. However, instead of subclassing
Django's AppConfig as seen `in the Django documentation
<https://docs.djangoproject.com/en/1.8/ref/applications/#for-application-authors>`_,
Pulp Plugins identify themselves as plugins to the Pulp Platform by subclassing
:class:`pulpcore.plugin.PulpPluginAppConfig` instead of ``django.apps.AppConfig``. ``PulpPluginAppConfig``
also provides the application autoloading behaviors, such as automatic registration of
viewsets with the API router, necessary for Pulp plugins.

The ``PulpPluginAppConfig`` subclass for any plugin must set its ``name`` attribute to
the importable dotted Python location of the plugin application (the Python namespace
that contains at least models and viewsets). Additionally, it should also set its ``label``
attribute to something that unambiguously labels which plugin is represented by that
subclass.

pulpcore.plugin Entry Point
---------------------------

The Pulp Platform discovers available plugins by inspecting the pulp.plugin entry point.

Once a plugin has defined its ``PulpPluginAppConfig`` subclass, it should add a pointer
to that subclass using the Django ``default_app_config`` convention, e.g.
``default_app_config = pulp_myplugin.app.MyPulpPluginAppConfig`` somewhere in the module
that contains your Django application. The Pulp Platform can then be told to use this value
to discover your plugin, by pointing the pulp.plugin entry point at it. If, for example, we
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

Model, Serializer, Viewset Discovery
------------------------------------

The structure of plugins should, where possible, mimic the layout of the Pulp Plugin API.
For example, model classes should be based on platform classes imported from
:mod:`pulp.plugin.models` and be defined in the ``models`` module of a plugin app. ViewSets
should be imported from :mod:`pulp.plugin.viewsets`, and be defined in the ``viewsets`` module
of a plugin app, and so on.

This matching of module names is required for the Pulp Platform to be able to auto-discover
plugin components, particularly for both models and viewsets.

Subclassing Importer, Publisher
-------------------------------

Error Handling
--------------

Please see the :ref:`error-handling` section in the code guidelines.

Non fatal exceptions should be recorded with the
:meth:`~pulpcore.plugin.tasking.Task.append_non_fatal_error` method. These non-fatal exceptions
will be returned in a :attr:`~pulpcore.app.models.Task.non_fatal_errors` attribute on the resulting
:class:`~pulpcore.app.models.Task` object.
