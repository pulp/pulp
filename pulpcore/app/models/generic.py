"""
Container for models using generic relations provided by Django's ContentTypes framework.

References:
    https://docs.djangoproject.com/en/1.8/ref/contrib/contenttypes/#generic-relations
"""

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from pulpcore.app.models.base import Model


class GenericRelationModel(Model):
    """Base model class for implementing Generic Relations.

    This class provides the required fields to implement generic relations. Instances of
    this class can only be related models with a primary key, such as those subclassing
    Pulp's base Model class.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        abstract = True
