"""pulp URL Configuration"""

import warnings

from django.core.exceptions import AppRegistryNotReady
from django.conf.urls import url, include
from rest_framework_nested import routers

from pulpcore.app.apps import pulp_plugin_configs
from pulpcore.app.views import ContentView, StatusView

root_router = routers.DefaultRouter(
    schema_title='Pulp API',
    schema_url='/api/v3'
)  #: The Pulp Platform v3 API router, which can be used to manually register ViewSets with the API.

# Load non-nested viewsets first, so we can make nested routers with them.
for app_config in pulp_plugin_configs():
    for viewset in app_config.named_viewsets.values():
        if not viewset.nest_prefix:
            viewset.register_with(root_router)


nested_routers = (
    routers.NestedDefaultRouter(root_router, 'repositories', lookup='repository'),
)


def router_for_nested_viewset(viewset):
    """
    Find the router for a nested viewset.

    Args:
        viewset (pulpcore.app.viewsets.NamedModelViewSet): a viewset for which a nested router
            should exist

    Returns:
        routers.NestedDefaultRouter: the nested router whose parent_prefix corresponds to the
            viewset's nest_prefix attribute.

    Raises:
        LookupError: if no nested router is found for the viewset.

    """
    for nrouter in nested_routers:
        if nrouter.parent_prefix == viewset.nest_prefix:
            return nrouter
    raise LookupError('No nested router has prefix {}'.format(viewset.nest_prefix))


# go through nested viewsets and register them
try:
    for app_config in pulp_plugin_configs():
        for viewset in app_config.named_viewsets.values():
            if viewset.nest_prefix:
                router = router_for_nested_viewset(viewset)
                viewset.register_with(router)
except AppRegistryNotReady as ex:
    # urls is being imported outside of an initialized django project, probably by a docs builder
    # or something else trying to inspect this module. Instead of exploding here and preventing the
    # import from succeeding, throw a warning explaining what's happening.
    warnings.warn("Unable to register plugin viewsets with API router, {}".format(ex.args[0]))


urlpatterns = [
    url(r'^{}/'.format(ContentView.BASE_PATH), ContentView.as_view()),
    url(r'^api/v3/', include(root_router.urls)),
    url(r'^api/v3/status/', StatusView.as_view()),
]


for nrouter in nested_routers:
    urlpatterns.append(url(r'^api/v3/', include(nrouter.urls)))
