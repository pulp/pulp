"""pulp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from rest_framework import routers

from pulp.app.apps import pulp_plugin_configs

router = routers.DefaultRouter(
    schema_title='Pulp API',
    schema_url='/api/v3'
)

# go through plugin model viewsets and register them
for app_config in pulp_plugin_configs():
    for viewset in app_config.named_viewsets.values():
        viewset.register_with(router)


urlpatterns = [
    url(r'^api/v3/', include(router.urls)),
]
