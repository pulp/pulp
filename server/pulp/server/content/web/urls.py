from django.conf.urls import url

from pulp.server.content.web.views import ContentView

urlpatterns = [
    url(r'.+', ContentView.as_view(), name='content'),
]
