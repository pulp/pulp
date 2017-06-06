from importlib import import_module

from django import apps
from django.utils.module_loading import module_has_submodule

VIEWSETS_MODULE_NAME = 'viewsets'


def pulp_plugin_configs():
    """
    A generator of Pulp plugin AppConfigs

    This makes it easy to iterate over just the installed Pulp plugins when working
    with discovered plugin components.
    """
    for app_config in apps.apps.get_app_configs():
        if isinstance(app_config, PulpPluginAppConfig):
            yield app_config


class PulpPluginAppConfig(apps.AppConfig):
    """AppConfig class. Use this in plugins to identify your app as a Pulp plugin."""

    # Plugin behavior loading should happen in ready(), not in __init__().
    # ready() is called after all models are initialized, and at that point we should
    # be able to safely inspect the plugin modules to look for any components we need
    # to "register" with platform. The viewset registration below is based on Django's
    # own model importing method.

    def __init__(self, app_name, app_module):
        super(PulpPluginAppConfig, self).__init__(app_name, app_module)

        # Module containing viewsets eg. <module 'pulp_plugin.app.viewsets'
        # from 'pulp_plugin/app/viewsets.pyc'>. Set by import_viewsets().
        # None if the application doesn't have a viewsets module, automatically set
        # when this app becomes ready.
        self.viewsets_module = None

        # Mapping of model names to viewsets (viewsets unrelated to models are excluded)
        self.named_viewsets = None

    def ready(self):
        # register signals here as suggested in Django docs
        # https://docs.djangoproject.com/en/1.8/topics/signals/#connecting-receiver-functions
        import pulpcore.app.signals  # noqa

        self.import_viewsets()

    def import_viewsets(self):
        # circular import avoidance
        from pulpcore.app.viewsets import NamedModelViewSet

        self.named_viewsets = {}
        if module_has_submodule(self.module, VIEWSETS_MODULE_NAME):
            # import the viewsets module and track any interesting viewsets
            viewsets_module_name = '%s.%s' % (self.name, VIEWSETS_MODULE_NAME)
            self.viewsets_module = import_module(viewsets_module_name)
            for objname in dir(self.viewsets_module):
                obj = getattr(self.viewsets_module, objname)
                try:
                    # Any subclass of NamedModelViewSet that isn't itself NamedModelViewSet
                    # gets registered in the named_viewsets registry.
                    if (obj is not NamedModelViewSet and
                            issubclass(obj, NamedModelViewSet)):
                        model = obj.queryset.model
                        self.named_viewsets[model] = obj
                except TypeError:
                    # obj isn't a class, issubclass exploded but obj can be safely filtered out
                    continue


class PulpAppConfig(PulpPluginAppConfig):
    # The pulpcore platform app is itself a pulpcore plugin so that it can benefit from
    # the component discovery mechanisms provided by that superclass.

    # The app's importable name
    name = 'pulpcore.app'

    # The app label to be used when creating tables, registering models, referencing this app
    # with manage.py, etc. This cannot contain a dot and must not conflict with the name of a
    # package containing a Django app.
    label = 'pulp_app'
