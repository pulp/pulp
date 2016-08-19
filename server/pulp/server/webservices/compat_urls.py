"""
This module creates urlpatterns using the old syntax of Django <=  1.6
"""

from pulp.server.webservices import urls

from django.conf.urls import patterns


urlpatterns = patterns('', *urls.urlpatterns)
