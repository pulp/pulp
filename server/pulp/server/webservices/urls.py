from django.conf.urls import patterns, url

from pulp.server.webservices.views.content import (
    ContentTypesView, ContentTypeResourceView, ContentUnitsCollectionView,
)
from pulp.server.webservices.views.repositories import RepoSync
from pulp.server.webservices.views.tasks import TasksView


urlpatterns = patterns('',
    url(r'^v2/content/types/$', ContentTypesView.as_view(),
        name='content_types'),
    url(r'^v2/content/types/(?P<type_id>\w+)/$', ContentTypeResourceView.as_view(),
        name='content_type_resource'),
    url(r'^v2/content/units/(?P<type_id>\w+)/$', ContentUnitsCollectionView.as_view(),
        name='content_units_collection'),
    url(r'^v2/repositories/(?P<repo_id>\w+)/actions/sync/$', RepoSync.as_view()),
    url(r'^v2/tasks/$', TasksView.as_view()),
)
