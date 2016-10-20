from rest_framework import serializers
from rest_framework.reverse import reverse

from pulp.app import models
from pulp.app.serializers import DetailRelatedField


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


class RepositoryNestedIdentityField(serializers.HyperlinkedIdentityField):
    """
    Used to represent an href identity field includes the associated repository name in the url.

    Overrides `get_url` and `get_object` methods. This is necessary because objects that are nested
    within their related repositories need to be able to generate their identity urls. The base
    implementation only supports a single url parameter, defined by `lookup_field`. By overriding
    these methods, we will use the repository name and the object name. In order for this to work,
    the object's `lookup_field` must be set to `name`.
    """

    def get_url(self, obj, view_name, request, format):
        """
        The parent class's get_url can only use a single kwarg, which is `lookup_field`. This
        builds a url that includes the associated repository name.
        """
        url_kwargs = {
            'repo_name': obj.repository.name,
            'name': obj.name
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)

    def get_object(self, view_name, view_args, view_kwargs):
        """
        Used to query for an object from its name and associated repository name.
        """
        lookup_kwargs = {
            'repository__name': view_kwargs['repo_name'],
            'name': view_kwargs['name']
        }
        return self.get_queryset().get(**lookup_kwargs)
