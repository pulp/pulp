"""
Django models related to content consumers.
"""

from django.db import models

from pulpcore.app.models import Model, Notes, GenericKeyValueRelation


class Consumer(Model):
    """
    A content consumer.

    Fields:

        name (~django.db.models.TextField): The consumer common name.
        description (~django.db.models.TextField): An optional description.

    Relations:

        notes (GenericKeyValueRelation): Arbitrary information about the consumer.
        publishers (~django.db.models.ManyToManyField): Associated publishers.

    """
    name = models.TextField(db_index=True, unique=True)
    description = models.TextField(blank=True)

    notes = GenericKeyValueRelation(Notes)
    publishers = models.ManyToManyField('Publisher', related_name='consumers')

    def natural_key(self):
        """
        Get the model's natural key.

        :return: The model's natural key.
        :rtype: tuple
        """
        return (self.name,)


class ConsumerContent(Model):
    """
    Collection of content currently installed on a consumer.

    Relations:

        consumer (~django.db.models.ForeignKey): The consumer on which the content is installed.
    """
    consumer = models.ForeignKey(Consumer, on_delete=models.CASCADE)

    class Meta:
        abstract = True
