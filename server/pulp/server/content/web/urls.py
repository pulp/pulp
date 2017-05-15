from django.conf.urls import patterns, url

from pulp.server.content.web.views import ContentView

urlpatterns = [
    url(r'.+', ContentView.as_view(), name='content'),
]
