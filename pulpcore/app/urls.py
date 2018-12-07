"""pulp URL Configuration"""
from django.conf.urls import url, include
from drf_yasg.views import get_schema_view as yasg_get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from rest_framework.schemas import get_schema_view
from rest_framework_nested import routers

from pulpcore.app.apps import pulp_plugin_configs
from pulpcore.app.openapigenerator import PulpOpenAPISchemaGenerator
from pulpcore.app.views import ContentView, OrphansView, StatusView
from pulpcore.constants import API_ROOT

import logging
log = logging.getLogger(__name__)


class ViewSetNode:
    """
    Each node is a tree that can register nested ViewSets with DRF nested routers.

    The structure of the tree becomes the url heirarchy when the ViewSets are registered.

    Example Structure:

        RootNode
        ├─ RepositoryViewSet
        │  ├─ PluginPublisherViewSet (non-nested)
        │  │  └─ DistributionViewSet
        │  ├─ AnotherPluginPublisherViewSet
        │  │  └─ DistributionViewSet (This node is attached to all Publisher Detail parents)
        │  └─ FileRemoteViewSet
        └─ some-non-nested viewset
    """

    def __init__(self, viewset=None):
        """
        Create a new node.

        Args:
            viewset (pulpcore.app.viewsets.base.NamedModelViewSet): If provided, represent this
                viewset. If not provided, this is the root node.
        """
        self.viewset = viewset
        self.children = []

    def add_decendent(self, node):
        """
        Add a VSNode to the tree. If node is not a direct child, attempt to add the to each child.

        Some nodes must be added more than once if they have a Master/Detail parent. Using
        Distributions as an example, DistributionViewset.parent_viewset is PublisherViewSet, which
        is a MasterViewset. Each of the publisher detail viewsets like FilePublisherViewSEt will
        have its own router, and the DistributionViewSet must be registered with each.

        Args:
            node (ViewSetNode): A node that represents a viewset and its decendents.
        """
        # Master viewsets do not have endpoints, so they do not need to be registered
        if node.viewset.is_master_viewset():
            return
        # Non-nested viewsets are attached to the root node
        if not node.viewset.parent_viewset:
            self.children.append(node)
        # The node is a direct child if the child.parent_viewset == self.viewset and also
        # if child.viewset is a master viewset and self.viewset is one of its detail viewsets.
        elif self.viewset and issubclass(self.viewset, node.viewset.parent_viewset):
            self.children.append(node)
        else:
            for child in self.children:
                child.add_decendent(node)

    def register_with(self, router):
        """
        Register this tree with the specified router and create new routers as necessary.

        Args:
            router (routers.DefaultRouter): router to register the viewset with.
            created_routers (list): A running list of all routers.
        Returns:
            list: List of new routers, including those created recursively.
        """
        created_routers = []
        # Root node does not need to be registered, and it doesn't need a router either.
        if self.viewset:
            router.register(self.viewset.urlpattern(), self.viewset, self.viewset.view_name())
            if self.children:
                router = routers.NestedDefaultRouter(router, self.viewset.urlpattern(),
                                                     lookup=self.viewset.router_lookup)
                created_routers.append(router)
        # If we created a new router for the parent, recursively register the children with it
        for child in self.children:
            created_routers = created_routers + child.register_with(router)
        return created_routers

    def __repr__(self):
        if not self.viewset:
            return "Root"
        else:
            return str(self.viewset)


all_viewsets = []
plugin_patterns = []
# Iterate over each app, including pulpcore and the plugins.
for app_config in pulp_plugin_configs():
    for viewset in app_config.named_viewsets.values():
        all_viewsets.append(viewset)
    if app_config.urls_module:
        plugin_patterns.append(app_config.urls_module)

sorted_by_depth = sorted(all_viewsets, key=lambda vs: vs._get_nest_depth())
vs_tree = ViewSetNode()
for viewset in sorted_by_depth:
    vs_tree.add_decendent(ViewSetNode(viewset))

#: The Pulp Platform v3 API router, which can be used to manually register ViewSets with the API.
root_router = routers.DefaultRouter()

urlpatterns = [
    url(r'^{}/'.format(ContentView.BASE_PATH), ContentView.as_view(), name='content-app'),
    url(r'^{api_root}status/'.format(api_root=API_ROOT), StatusView.as_view()),
    url(r'^{api_root}orphans/'.format(api_root=API_ROOT), OrphansView.as_view()),
    url(r'^auth/', include('rest_framework.urls')),
]

docs_schema_view = yasg_get_schema_view(
    openapi.Info(
        title="Pulp3 API",
        default_version='v3',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    generator_class=PulpOpenAPISchemaGenerator,
)
urlpatterns.append(url(
    r'^{api_root}docs/api(?P<format>\.json|\.yaml)'.format(api_root=API_ROOT),
    docs_schema_view.without_ui(cache_timeout=None),
    name='schema-json')
)

urlpatterns.append(url(
    r'^{api_root}docs/'.format(api_root=API_ROOT),
    docs_schema_view.with_ui('redoc', cache_timeout=None),
    name='schema-redoc')
)

schema_view = get_schema_view(title='Pulp API')

urlpatterns.append(url(r'^{api_root}$'.format(api_root=API_ROOT), schema_view))

all_routers = [root_router] + vs_tree.register_with(root_router)
for router in all_routers:
    urlpatterns.append(url(r'^{api_root}'.format(api_root=API_ROOT), include(router.urls)))

# If plugins define a urls.py, include them into the root namespace.
for plugin_pattern in plugin_patterns:
    urlpatterns.append(url(r'', include(plugin_pattern)))
