from pulpcore.app.models import DownloadCatalog
from pulpcore.app.pagination import ImporterPagination
from pulpcore.app.serializers import DownloadCatalogSerializer
from pulpcore.app.viewsets import NamedModelViewSet


class DownloadCatalogViewSet(NamedModelViewSet):
    endpoint_name = 'downloadcatalogs'
    queryset = DownloadCatalog.objects.all()
    serializer_class = DownloadCatalogSerializer
    pagination_class = ImporterPagination
    http_method_names = ['get', 'options']
