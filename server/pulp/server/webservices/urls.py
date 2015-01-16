from django.conf.urls import patterns, url

from pulp.server.webservices.views.content import (
    ContentTypesView, ContentTypeResourceView, ContentUnitsCollectionView,
)
from pulp.server.webservices.views.plugins import (DistributorResourceView, DistributorsView,
                                                   ImporterResourceView, ImportersView,
                                                   TypeResourceView, TypesView)
from pulp.server.webservices.views.repositories import RepoSync
from pulp.server.webservices.views.tasks import TasksView


urlpatterns = patterns('',
    url(r'^v2/content/types/$', ContentTypesView.as_view(),
        name='content_types'),
    url(r'^v2/content/types/(?P<type_id>[^/]+)/$', ContentTypeResourceView.as_view(),
        name='content_type_resource'),
    url(r'^v2/content/units/(?P<type_id>[^/]+)/$', ContentUnitsCollectionView.as_view(),
        name='content_units_collection'),
    url(r'^v2/distributors/$', DistributorsView.as_view()),
    url(r'^v2/distributors/(?P<distributor_type_id>[^/]+)/$', DistributorResourceView.as_view()),
    url(r'^v2/plugins/importers/$', ImportersView.as_view()),
    url(r'^v2/plugins/importers/(?P<importer_type_id>[^/]+)/$', ImporterResourceView.as_view()),
    url(r'^v2/plugins/types/$', TypesView.as_view(), name='plugin_types'),
    url(r'^v2/plugins/types/(?P<type_id>[^/]+)/$', TypeResourceView.as_view()),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/actions/sync/$', RepoSync.as_view()),
    url(r'^v2/tasks/$', TasksView.as_view()),
)
