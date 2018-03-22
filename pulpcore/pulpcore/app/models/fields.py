from django.db.models import FileField

from pulpcore.app.files import TemporaryDownloadedFile


class ArtifactFileField(FileField):
    """
    A custom FileField that always saves files to location specified by 'upload_to'

    The field can be set as either a path to the file or File object. In both cases the file is
    moved or copied to the location specified by 'upload_to' field parameter.
    """
    def pre_save(self, model_instance, add):
        """
        Returns path to the file to be stored in database

        Args:
            model_instance (`class::pulpcore.plugin.Artifact`): The instance this field belongs to.
            add (bool): Whether the instance is being saved to the database for the first time.

        Returns:
            Field's value just before saving.
        """
        file = super().pre_save(model_instance, add)
        if file and file._committed and add:
            file._file = TemporaryDownloadedFile(open(file.name, 'rb'))
            file._committed = False
        return super().pre_save(model_instance, add)
