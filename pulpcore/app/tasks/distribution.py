from django.core.exceptions import ObjectDoesNotExist
from pulpcore.app.models import Distribution
from pulpcore.app.serializers import DistributionSerializer


def create(*args, **kwargs):
    """
    Creates a :class:`~pulpcore.app.models.Distribution`
    """
    data = kwargs.pop('data', None)
    serializer = DistributionSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    serializer.save()


def update(instance_id, *args, **kwargs):
    """
    Updates a :class:`~pulpcore.app.models.Distribution`

    Args:
        instance_id (int): The id of the distribution to be updated
    """
    data = kwargs.pop('data', None)
    partial = kwargs.pop('partial', False)
    instance = Distribution.objects.get(pk=instance_id)
    serializer = DistributionSerializer(instance, data=data, partial=partial)
    serializer.is_valid(raise_exception=True)
    serializer.save()


def delete(instance_id, *args, **kwargs):
    """
    Delete a :class:`~pulpcore.app.models.Distribution`

    Args:
        instance_id (int): The id of the Distribution to be deleted
    """
    try:
        instance = Distribution.objects.get(pk=instance_id)
    except ObjectDoesNotExist:
        #
        return
    else:
        instance.delete()
