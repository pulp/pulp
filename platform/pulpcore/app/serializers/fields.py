from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse


from pulpcore.app import models
from pulpcore.app.serializers import DetailRelatedField


class ContentRelatedField(DetailRelatedField):
    """
    Serializer Field for use when relating to Content Detail Models
    """
    queryset = models.Content.objects.all()


class RepositoryRelatedField(serializers.HyperlinkedRelatedField):
    """
    A serializer field with the correct view_name and lookup_field to link to a repository.
    """
    view_name = 'repositories-detail'
    lookup_field = 'name'
    queryset = models.Repository.objects.all()


class FileField(serializers.CharField):
    """
    Serializer Field for model.FileField and REST API passing file content.
    """

    def to_internal_value(self, data):
        return models.FileContent(data)

    def to_representation(self, value):
        return str(value)

class ContentArtifactsField(serializers.DictField):
    """
    A serializer field for the 'artifacts' ManyToManyField on the Content model.
    """

    def run_validation(self, data):
        """
        Validate that all keys of 'data' correspond to existing Artifacts.

        Args:
            data (dict): A dict mapping Artifact URLs to the corresponding relative path of the
                artifact inside the Content.

        Returns:
            A dict mapping Artifact instances to the corresponding relative path of the
                artifact inside the Content.

        Raises:
            :class:`rest_framework.exceptions.ValidationError`: When one of the Artifacts does not
                exist.
        """
        ret = {}
        for key, val in data.items():
            artifactfield = serializers.HyperlinkedRelatedField(view_name='artifacts-detail',
                                                                queryset=models.Artifact.objects.all(),
                                                                source='*', initial=key)
            artifactfield.context=self.context
            try:
                artifact = artifactfield.run_validation(data=key)
                ret[artifact] = val
            except ValidationError as e:
                # Append the URL of missing Artifact to the error message
                e.detail[0] = "%s %s" % (e.detail[0], key)
                raise e
        return ret

    def get_attribute(self, instance):
        """
        Returns the field from the instance that should be serialized using this serializer field.

        This serializer field serializes a ManyToManyField that is actually stored as a
        ContentArtifact model. Instead of returning the field, this method returns all the
        ContentArtifact models related to this Content.

        Args:
            instance (:class:`pulpcore.app.models.Content`): An instance of Content being serialized.

        Returns:
            A list of ContentArtifact models related to the instance of Content.
        """
        return models.ContentArtifact.objects.filter(content=instance)

    def to_representation(self, value):
        """
        Serializes list of ContentArtifacts.

        Returns a dict mapping Artifact URLs to the corresponding relative path of the artifact
        inside the Content.

        Args:
            value (list of :class:`pulpcore.app.models.ContentArtifact`): A list of all the
            ContentArtifacts related to the Content model being serialized.

        Returns:
            A dict mapping Artifact URLs to the corresponding relative path of the
                artifact inside the Content.
        """
        ret = {}
        for content_artifact in value:
            url = reverse('artifacts-detail', kwargs={'pk': content_artifact.artifact_id}, request=self.context['request'])
            ret[url] = content_artifact.relative_path
        return ret


