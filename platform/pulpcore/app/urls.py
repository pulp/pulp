"""pulp URL Configuration"""

import warnings

from django.core.exceptions import AppRegistryNotReady
from django.conf.urls import url, include
from rest_framework import routers

from pulpcore.app.apps import pulp_plugin_configs

router = routers.DefaultRouter(
    schema_title='Pulp API',
    schema_url='/api/v3'
)  #: The Pulp Platform v3 API router, which can be used to manually register ViewSets with the API.

# go through plugin model viewsets and register them
try:
    for app_config in pulp_plugin_configs():
        for viewset in app_config.named_viewsets.values():
            viewset.register_with(router)
except AppRegistryNotReady as ex:
    # urls is being imported outside of an initialized django project, probably by a docs builder
    # or something else trying to inspect this module. Instead of exploding here and preventing the
    # import from succeeding, throw a warning explaining what's happening.
    warnings.warn("Unable to register plugin viewsets with API router, {}".format(ex.args[0]))

urlpatterns = [
    url(r'^api/v3/', include(router.urls)),
]
