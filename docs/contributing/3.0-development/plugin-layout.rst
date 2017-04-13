Pulp Plugin Application Layout
==============================

This documentation is for Pulp Plugin developers. For Platform development,
see the :doc:`app-layout`.

The Pulp Platform does not manage any content itself. This functionality is provided by
its plugins, which use the Pulp Platform Plugin API to manage specific types of content,
like RPM Packages or Puppet Modules. To do this, the Pulp Platform extends the Django
Web Framework and the Django REST Framework to provide a set of base classes that can be
implemented in plugins to manage content in a way that is consistent across plugins, while
still allowing plugin writers the freedom to define their workflows as they deem necessary.


Plugin API
----------

The Pulp :doc:`../plugin_api/index` is versioned separately from the Pulp Platform, and consists
of everything importable withing the :mod:`pulp.plugin` namespace. When writing plugins, care should
be taken to only import Pulp Platform components exposed in this namespace; importing from elsewhere
within the Pulp Platform (e.g. importing directly from ``pulp.app``, ``pulp.exceptions``, etc.)
is unsupported, and not protected by the Pulp Plugin API's semantic versioning guarantees.

.. warning::

    Exactly what is versioned in the Plugin API, and how, still has yet to be determined.
    This documentation will be updated to clearly identify what guarantees come with the
    semantic versioning of the Plugin API in the future. As our initial plugins are under
    development prior to the release of Pulp 3.0, the Plugin API can be assumed to have
    semantic major version 0, indicating it is unstable and still being developed.


Plugin Application
------------------

Like the Pulp Platform itself, all Pulp Plugins begin as Django Applications, started like
any other with ``django-admin startapp <your_plugin>``. However, instead of subclassing
Django's AppConfig as seen `in the Django documentation
<https://docs.djangoproject.com/en/1.8/ref/applications/#for-application-authors>`_,
Pulp Plugins identify themselves as plugins to the Pulp Platform by subclassing
:class:`pulp.plugin.PulpPluginAppConfig` instead of ``django.apps.AppConfig``. ``PulpPluginAppConfig``
also provides the application autoloading behaviors, such as automatic registration of
viewsets with the API router, necessary for Pulp plugins.

The ``PulpPluginAppConfig`` subclass for any plugin must set its ``name`` attribute to
the importable dotted Python location of the plugin application (the Python namespace
that contains at least models and viewsets). Additionally, it should also set its ``label``
attribute to something that unambiguously labels which plugin is represented by that
subclass.

pulp.plugin Entry Point
-----------------------

The Pulp Platform discovers available plugins by inspecting the pulp.plugin entry point.

Once a plugin has defined its ``PulpPluginAppConfig`` subclass, it should add a pointer
to that subclass using the Django ``default_app_config`` convention, e.g.
``default_app_config = pulp_myplugin.app.MyPulpPluginAppConfig`` somewhere in the module
that contains your Django application. The Pulp Platform can then be told to use this value
to discover your plugin, by pointing the pulp.plugin entry point at it. If, for example, we
set ``default_app_config`` in ``pulp_myplugin/__init__.py``, the setup.py ``entry_points``
would look like this::

    entry_points={
        'pulp.plugin': [
            'pulp_myplugin = pulp_myplugin:default_app_config',
        ]
    }

If you do not wish to use Django's ``default_app_config`` convention, the name given to
the ``pulp.plugin`` entry point must be an importable identifier with a string value
containing the importable dotted path to your plugin's application config class, just
as ``default_app_config`` does.


Plugin Structure
----------------

The structure of plugins should, where possible, mimic the layout of the Pulp Plugin API.
For example, model classes should be based on platform classes imported from
:mod:`pulp.plugin.models` and be defined in the ``models`` module of a plugin app. ViewSets
should be imported from :mod:`pulp.plugin.viewsets`, and be defined in the ``viewsets`` module
of a plugin app, and so on.

This matching of module names is required for the Pulp Platform to be able to auto-discover
plugin components, particularly for both models and viewsets.
