from django.conf.urls import patterns, url

from pulp.server.content.web.views import ContentView

# View Prefix
PREFIX = ''

# Patterns
urlpatterns = patterns(
    PREFIX,
    url(r'.+', ContentView.as_view(), name='content'),
)
