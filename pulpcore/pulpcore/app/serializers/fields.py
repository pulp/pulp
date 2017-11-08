from gettext import gettext as _
import os

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


class HrefWritableRepositoryRelatedField(serializers.HyperlinkedRelatedField):
    """
    A serializer field for a repository that is the parent in a nested relationship.
    It has the href_writable field set so the repository is determined by url parameters.
    read_only should passed as a kwarg to this field.
    """
    view_name = 'repositories-detail'
    lookup_field = 'name'
    href_writable = True


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
        Validates 'data' dict.

        Validates that all keys of 'data' are relative paths. Validates that all values of 'data'
        are URLs for an existing Artifact.

        Args:
            data (dict): A dict mapping relative paths inside the Content to the corresponding
                Artifact URLs.

        Returns:
            A dict mapping relative paths inside the Content to the corresponding Artifact
                instances.

        Raises:
            :class:`rest_framework.exceptions.ValidationError`: When one of the Artifacts does not
                exist or one of the paths is not a relative path.
        """
        ret = {}
        for relative_path, url in data.items():
            if os.path.isabs(relative_path):
                raise ValidationError(_("Relative path can't start with '/'. "
                                        "{0}").format(relative_path))
            artifactfield = \
                serializers.HyperlinkedRelatedField(view_name='artifacts-detail',
                                                    queryset=models.Artifact.objects.all(),
                                                    source='*', initial=url)
            try:
                artifact = artifactfield.run_validation(data=url)
                ret[relative_path] = artifact
            except ValidationError as e:
                # Append the URL of missing Artifact to the error message
                e.detail[0] = "%s %s" % (e.detail[0], url)
                raise e
        return ret

    def get_attribute(self, instance):
        """
        Returns the field from the instance that should be serialized using this serializer field.

        This serializer field serializes a ManyToManyField that is actually stored as a
        ContentArtifact model. Instead of returning the field, this method returns all the
        ContentArtifact models related to this Content.

        Args:
            instance (:class:`pulpcore.app.models.Content`): An instance of Content being
                serialized.

        Returns:
            A list of ContentArtifact models related to the instance of Content.
        """
        return instance.contentartifact_set.all()

    def to_representation(self, value):
        """
        Serializes list of ContentArtifacts.

        Returns a dict mapping relative paths inside the Content to the corresponding Artifact
        URLs.

        Args:
            value (list of :class:`pulpcore.app.models.ContentArtifact`): A list of all the
                ContentArtifacts related to the Content model being serialized.

        Returns:
            A dict where keys are relative path of the artifact inside the Content and values are
                Artifact URLs.
        """
        ret = {}
        for content_artifact in value:
            if content_artifact.artifact_id:
                url = reverse('artifacts-detail', kwargs={'pk': content_artifact.artifact_id},
                              request=self.context['request'])
            else:
                url = None
            ret[content_artifact.relative_path] = url
        return ret
