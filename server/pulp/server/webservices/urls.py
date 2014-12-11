from django.conf.urls import patterns, url

from pulp.server.webservices.views.plugins import (DistributorResourceView, DistributorsView,
                                                   ImporterResourceView, ImportersView,
                                                   TypeResourceView, TypesView)
from pulp.server.webservices.views.root_actions import LoginView
from pulp.server.webservices.views.repositories import RepoSync
from pulp.server.webservices.views.repo_groups import (
    RepoGroupAssociateView, RepoGroupDistributorResource, RepoGroupDistributorsView,
    RepoGroupPublishView, RepoGroupResourceView, RepoGroupsView, RepoGroupUnassociateView
)
from pulp.server.webservices.views.tasks import TasksView


urlpatterns = patterns('',
    url(r'^v2/actions/login/$', LoginView.as_view(), name='login'),
    url(r'^v2/distributors/$', DistributorsView.as_view()),
    url(r'^v2/distributors/(?P<distributor_type_id>[^/]+)/$', DistributorResourceView.as_view()),
    url(r'^v2/plugins/importers/$', ImportersView.as_view()),
    url(r'^v2/plugins/importers/(?P<importer_id>[^/]+)/$', ImporterResourceView.as_view(),
        name='plugin_importer_resource'),
    url(r'^v2/plugins/types/$', TypesView.as_view(), name='plugin_types'),
    url(r'^v2/plugins/types/(?P<type_id>[^/]+)/$', TypeResourceView.as_view(),
        name='plugin_type_resource'),
    url(r'^v2/repo_groups/$', RepoGroupsView.as_view(), name='repo_groups'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/$', RepoGroupResourceView.as_view(),
        name='repo_group_resource'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/actions/associate/$',
        RepoGroupAssociateView.as_view(), name='repo_group_associate'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/actions/publish/$',
        RepoGroupPublishView.as_view(), name='repo_group_publish'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/actions/unassociate/$',
        RepoGroupUnassociateView.as_view(), name='repo_group_unassociate'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/distributors/$',
        RepoGroupDistributorsView.as_view(), name='repo_group_distributors'),
    url(r'^v2/repo_groups/(?P<repo_group_id>[^/]+)/distributors/(?P<distributor_id>[^/]+)/$',
        RepoGroupDistributorResource.as_view(), name='repo_group_distributor_resource'),
    url(r'^v2/repositories/(?P<repo_id>[^/]+)/actions/sync/$', RepoSync.as_view(),
        name="repositories_resource_sync"),
    url(r'^v2/tasks/$', TasksView.as_view(), name='tasks')
)
