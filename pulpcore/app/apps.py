from importlib import import_module

from django import apps
from django.utils.module_loading import module_has_submodule

from pulpcore.exceptions.plugin import MissingPlugin

VIEWSETS_MODULE_NAME = 'viewsets'
SERIALIZERS_MODULE_NAME = 'serializers'
URLS_MODULE_NAME = 'urls'


def pulp_plugin_configs():
    """
    A generator of Pulp plugin AppConfigs

    This makes it easy to iterate over just the installed Pulp plugins when working
    with discovered plugin components.
    """
    for app_config in apps.apps.get_app_configs():
        if isinstance(app_config, PulpPluginAppConfig):
            yield app_config


def get_plugin_config(plugin_app_label):
    """
    A getter of specific pulp plugin config

    This makes it easy to retrieve a config for a specific Pulp plugin when looking for a
    registered model.

    Args:
        plugin_app_label (str): Django app label of the pulp plugin

    Returns:
        :class:`pulpcore.app.apps.PulpPluginAppConfig`: The app config of the Pulp plugin.

    Raises:
        MissingPlugin: When plugin with the requested app label is not installed.
    """
    for config in pulp_plugin_configs():
        if config.label == plugin_app_label:
            return config
    raise MissingPlugin(plugin_app_label)


class PulpPluginAppConfig(apps.AppConfig):
    """AppConfig class. Use this in plugins to identify your app as a Pulp plugin."""

    # Plugin behavior loading should happen in ready(), not in __init__().
    # ready() is called after all models are initialized, and at that point we should
    # be able to safely inspect the plugin modules to look for any components we need
    # to "register" with pulpcore. The viewset registration below is based on Django's
    # own model importing method.

    def __init__(self, app_name, app_module):
        super().__init__(app_name, app_module)

        # Module containing viewsets eg. <module 'pulp_plugin.app.viewsets'
        # from 'pulp_plugin/app/viewsets.py'>. Set by import_viewsets().
        # None if the application doesn't have a viewsets module, automatically set
        # when this app becomes ready.
        self.viewsets_module = None

        # Module containing urlpatterns
        self.urls_module = None

        # Mapping of model names to viewsets (viewsets unrelated to models are excluded)
        self.named_viewsets = None
        # Mapping of serializer names to serializers
        self.named_serializers = None

    def ready(self):
        self.import_viewsets()
        self.import_serializers()
        self.import_urls()

    def import_serializers(self):
        # circular import avoidance
        from pulpcore.app.serializers import ModelSerializer

        self.named_serializers = {}
        if module_has_submodule(self.module, SERIALIZERS_MODULE_NAME):
            # import the serializers module and track any discovered serializers
            serializers_module_name = '{name}.{module}'.format(
                name=self.name, module=SERIALIZERS_MODULE_NAME)
            self.serializers_module = import_module(serializers_module_name)
            for objname in dir(self.serializers_module):
                obj = getattr(self.serializers_module, objname)
                try:
                    # Any subclass of ModelSerializer that isn't itself ModelSerializer
                    # gets registered in the named_serializers registry.
                    if obj is not ModelSerializer and issubclass(obj, ModelSerializer):
                        self.named_serializers[objname] = obj
                except TypeError:
                    # obj isn't a class, issubclass exploded but obj can be safely filtered out
                    continue

    def import_viewsets(self):
        # circular import avoidance
        from pulpcore.app.viewsets import NamedModelViewSet
        self.named_viewsets = {}
        if module_has_submodule(self.module, VIEWSETS_MODULE_NAME):
            # import the viewsets module and track any interesting viewsets
            viewsets_module_name = '{name}.{module}'.format(
                name=self.name, module=VIEWSETS_MODULE_NAME)
            self.viewsets_module = import_module(viewsets_module_name)
            for objname in dir(self.viewsets_module):
                obj = getattr(self.viewsets_module, objname)
                try:
                    # Any subclass of NamedModelViewSet that isn't itself NamedModelViewSet
                    # gets registered in the named_viewsets registry.
                    if (obj is not NamedModelViewSet and issubclass(obj, NamedModelViewSet)):
                        model = obj.queryset.model
                        self.named_viewsets[model] = obj
                except TypeError:
                    # obj isn't a class, issubclass exploded but obj can be safely filtered out
                    continue

    def import_urls(self):
        """
        If a plugin defines a urls.py, include it.
        """
        if module_has_submodule(self.module, URLS_MODULE_NAME) and self.name != "pulpcore.app":
            urls_module_name = '{name}.{module}'.format(
                name=self.name, module=URLS_MODULE_NAME)
            self.urls_module = import_module(urls_module_name)


class PulpAppConfig(PulpPluginAppConfig):
    # The pulpcore app is itself a pulpcore plugin so that it can benefit from
    # the component discovery mechanisms provided by that superclass.

    # The app's importable name
    name = 'pulpcore.app'

    # The app label to be used when creating tables, registering models, referencing this app
    # with manage.py, etc. This cannot contain a dot and must not conflict with the name of a
    # package containing a Django app.
    label = 'pulp_app'
