from django.conf.urls import patterns, url

from pulp.server.webservices.views.consumer_groups import (ConsumerGroupAssociateActionView,
                                                           ConsumerGroupBindingView,
                                                           ConsumerGroupBindingsView,
                                                           ConsumerGroupContentActionView,
                                                           ConsumerGroupResourceView,
                                                           ConsumerGroupUnassociateActionView)
from pulp.server.webservices.views.content import (
    CatalogResourceView, ContentTypeResourceView, ContentTypesView, ContentUnitResourceView,
    ContentUnitsCollectionView,ContentUnitUserMetadataResourceView,
    DeleteOrphansActionView, OrphanCollectionView, OrphanResourceView,
    OrphanTypeSubCollectionView, UploadResourceView,
    UploadSegmentResourceView
)
from pulp.server.webservices.views.plugins import (DistributorResourceView, DistributorsView,
                                                   ImporterResourceView, ImportersView,
                                                   TypeResourceView, TypesView)
from pulp.server.webservices.views.root_actions import LoginView
from pulp.server.webservices.views.dispatch import TaskCollectionView, TaskResourceView


urlpatterns = patterns('',
    url(r'^v2/actions/login/$', LoginView.as_view(), name='login'), # flake8: noqa
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)/$',
        ConsumerGroupResourceView.as_view(), name='consumer_group_resource'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)/actions/associate/$',
        ConsumerGroupAssociateActionView.as_view(), name='consumer_group_associate'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)/actions/unassociate/$',
        ConsumerGroupUnassociateActionView.as_view(), name='consumer_group_unassociate'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)/actions/content/(?P<action>[^/]+)/$',
        ConsumerGroupContentActionView.as_view(), name='consumer_group_content'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)/bindings/$',
        ConsumerGroupBindingsView.as_view(), name='consumer_group_bind'),
    url(r'^v2/consumer_groups/(?P<consumer_group_id>[^/]+)' +
        r'/bindings/(?P<repo_id>[^/]+)/(?P<distributor_id>[^/]+)/$',
        ConsumerGroupBindingView.as_view(), name='consumer_group_unbind'),
    url(r'^v2/content/actions/delete_orphans/$', DeleteOrphansActionView.as_view(),
        name='content_actions_delete_orphans'),
    url(r'^v2/content/catalog/(?P<source_id>[^/]+)/$', CatalogResourceView.as_view(),
        name='content_catalog_resource'),
    url(r'^v2/content/orphans/$', OrphanCollectionView.as_view(), name='content_orphan_collection'),
    url(r'^v2/content/orphans/(?P<content_type>[^/]+)/$', OrphanTypeSubCollectionView.as_view(),
        name='content_orphan_type_subcollection'),
    url(r'^v2/content/orphans/(?P<content_type>[^/]+)/(?P<unit_id>[^/]+)/$',
        OrphanResourceView.as_view(), name='content_orphan_resource'),
    url(r'^v2/content/types/$', ContentTypesView.as_view(),
        name='content_types'),
    url(r'^v2/content/types/(?P<type_id>[^/]+)/$', ContentTypeResourceView.as_view(),
        name='content_type_resource'),
    url(r'^v2/content/units/(?P<type_id>[^/]+)/$', ContentUnitsCollectionView.as_view(),
        name='content_units_collection'),
    url(r'^v2/content/units/(?P<type_id>[^/]+)/(?P<unit_id>[^/]+)/$',
        ContentUnitResourceView.as_view(), name='content_unit_resource'),
    url(r'^v2/content/units/(?P<type_id>[^/]+)/(?P<unit_id>[^/]+)/pulp_user_metadata/$',
        ContentUnitUserMetadataResourceView.as_view(), name='content_unit_user_metadata_resource'),
    url(r'^v2/content/uploads/(?P<upload_id>[^/]+)/$', UploadResourceView.as_view(),
        name='content_upload_resource'),
    url(r'^v2/content/uploads/(?P<upload_id>[^/]+)/(?P<offset>[^/]+)/$',
        UploadSegmentResourceView.as_view(), name='content_upload_segment_resource'),
    url(r'^v2/plugins/distributors/$', DistributorsView.as_view(), name='plugin_distributors'),
    url(r'^v2/plugins/distributors/(?P<distributor_id>[^/]+)/$', DistributorResourceView.as_view(),
        name='plugin_distributor_resource'),
    url(r'^v2/plugins/importers/$', ImportersView.as_view(), name='plugin_importers'),
    url(r'^v2/plugins/importers/(?P<importer_id>[^/]+)/$', ImporterResourceView.as_view(),
        name='plugin_importer_resource'),
    url(r'^v2/plugins/types/$', TypesView.as_view(), name='plugin_types'),
    url(r'^v2/plugins/types/(?P<type_id>[^/]+)/$', TypeResourceView.as_view(),
        name='plugin_type_resource'),
    url(r'^v2/tasks/$', TaskCollectionView.as_view(), name='task_collection'),
    url(r'^v2/tasks/(?P<task_id>[^/]+)/$', TaskResourceView.as_view(), name='task_resource'),
)
