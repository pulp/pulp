from django.conf.urls import patterns, url

from pulp.server.webservices.views.content import OrphanTypeSubCollectionView
from pulp.server.webservices.views.tasks import TasksView
from pulp.server.webservices.views.repositories import RepoSync


urlpatterns = patterns('',
    url(r'^v2/content/orphans/(?P<content_type>[^/]+)/$', OrphanTypeSubCollectionView.as_view(),
        name='orphan_type_subcollection'),
    url(r'^v2/tasks/$', TasksView.as_view()),
    url(r'^v2/repositories/(?P<repo_id>\w+)/actions/sync/$', RepoSync.as_view()),
)