from django.conf.urls import patterns, url

from pulp.server.webservices.views.content import (
    ContentUnitResourceView,
)
from pulp.server.webservices.views.tasks import TasksView


urlpatterns = patterns('',
    url(r'^v2/content/units/(?P<type_id>\w+)/(?P<unit_id>[\w-]+)/$',
        ContentUnitResourceView.as_view(), name='content_units_collection'),
    url(r'^v2/tasks/$', TasksView.as_view()),
)
