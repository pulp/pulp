"""
Django models related to content consumers.
"""

from django.contrib.contenttypes import fields
from django.db import models

from pulp.platform.models import Model, Notes


class Consumer(Model):
    """
    A content consumer.

    Fields:

    :cvar name: The consumer common name.
    :type name: models.TextField

    :cvar: description: An optional description.
    :type: models.TextField

    Relations:

    :cvar notes: Arbitrary information about the consumer.
    :type notes: fields.GenericRelation

    :cvar distributors: Associated distributors.
    :type distributors: models.ManyToManyField
    """
    name = models.TextField(db_index=True, unique=True)
    description = models.TextField(blank=True)

    notes = fields.GenericRelation(Notes)
    distributors = models.ManyToManyField('RepositoryDistributor')


class ConsumerContent(Model):
    """
    Collection of content currently installed on a consumer.

    Relations:

    :cvar consumer: The consumer on which the content is installed.
    :type consumer: models.ForeignKey
    """
    consumer = models.ForeignKey(Consumer, on_delete=models.CASCADE)

    class Meta:
        abstract = True
