from rest_framework import response, permissions
from drf_openapi.views import SchemaView
from drf_openapi.entities import OpenApiSchemaGenerator


class DocView(SchemaView):
    """
    REST API live documentation endpoint.

    Subclasses drf_openapi.views.SchemaView to provide a publicly accessible
    REST API documentation endpoint.
    """

    permission_classes = (permissions.AllowAny,)

    def get(self, request, version):
        """
        Override to mark schemas as public.

        :param request:
        :param version:
        :return:
        """
        generator = OpenApiSchemaGenerator(
            version=version,
            url=self.url,
            title=self.title
        )
        return response.Response(generator.get_schema(request, public=True))
