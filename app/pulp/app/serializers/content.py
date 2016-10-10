from pulp.app import models
from pulp.app.serializers import base, fields


class ContentSerializer(base.MasterModelSerializer):
    _href = base.DetailIdentityField()
    repositories = fields.RepositoryRelatedField(many=True)

    class Meta:
        model = models.Content
        fields = base.MasterModelSerializer.Meta.fields + ('repositories',)


class ContentRelatedField(base.DetailRelatedField):
    """
    Serializer Field for use when relating to Content Detail Models
    """
    queryset = models.Content.objects.all()
