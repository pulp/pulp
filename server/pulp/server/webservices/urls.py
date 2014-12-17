from django.conf.urls import patterns, url

from pulp.server.webservices.views.content import UploadResourceView
from pulp.server.webservices.views.tasks import TasksView
from pulp.server.webservices.views.repositories import RepoSync


urlpatterns = patterns('',
    url(r'^v2/content/uploads/(?P<upload_id>[^/]+)/$', UploadResourceView.as_view(),
        name='content_upload_resource'),
    url(r'^v2/repositories/(?P<repo_id>\w+)/actions/sync/$', RepoSync.as_view()),
    url(r'^v2/tasks/$', TasksView.as_view()),

)
