from django.conf.urls import patterns, include, url

from pulp.server.webservices.views.tasks import TasksView

urlpatterns = patterns('',
    url(r'^v2/tasks/$', TasksView.as_view()),
)
