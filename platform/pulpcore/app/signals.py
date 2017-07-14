import os

from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from pulpcore.app.models import Artifact
from pulpcore.app.models.storage import FileSystem


@receiver(pre_delete, sender=Artifact)
def artifact_pre_delete(sender, instance, **kwargs):
    """
    Delete artifact bits from a filesystem

    Args:
        sender (class): The model class
        instance (:class:`pulpcore.app.model.Artifact`): The actual instance being deleted.

    """
    artifact = instance
    units_root = os.path.join(settings.MEDIA_ROOT, 'artifact')
    artifact_dir = os.path.dirname(artifact.file.path)
    artifact.file.delete()
    FileSystem.delete_empty_dirs(artifact_dir, units_root)
