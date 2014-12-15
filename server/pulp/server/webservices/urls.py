from django.conf.urls import patterns, url

from pulp.server.webservices.views.content import (
    ContentUnitResourceView,
)
from pulp.server.webservices.views.tasks import TasksView
from pulp.server.webservices.views.repositories import RepoSync


urlpatterns = patterns('',
    url(r'^v2/content/units/(?P<type_id>\w+)/(?P<unit_id>[\w-]+)/$',
        ContentUnitResourceView.as_view(), name='content_units_collection'),
    url(r'^v2/tasks/$', TasksView.as_view()),
    url(r'^v2/repositories/(?P<repo_id>\w+)/actions/sync/$', RepoSync.as_view()),
)
