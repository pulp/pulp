from django.conf.urls import patterns, url

from pulp.server.webservices.views.content import OrphanResourceView
from pulp.server.webservices.views.tasks import TasksView
from pulp.server.webservices.views.repositories import RepoSync


urlpatterns = patterns('',
    url(r'^v2/content/orphans/(?P<content_type>[^/]+)/(?P<unit_id>[^/]+)/$',
        OrphanResourceView.as_view(), name='orphan_resource'),
    url(r'^v2/tasks/$', TasksView.as_view()),
    url(r'^v2/repositories/(?P<repo_id>\w+)/actions/sync/$', RepoSync.as_view()),
)
