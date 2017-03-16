from pulp.app.models import Importer as PlatformImporter
from pulp.download import DigestValidation, HttpDownload, SizeValidation


class Importer(PlatformImporter):
    """
    The base importer object to sync content.

    This is meant to be subclassed by plugin authors as an opportunity to provide:

    * Plugin specific sync functionality
    * Add persistent data attributes for a plugin importer subclass
    * Additional validation of plugin importer subclass configuration

    The sync implementation is provided by :meth: `Importer.sync` which provides more details.
    Failing to implement this method will prevent sync functionality for this plugin type.

    This object is a Django model that inherits from :class: `pulp.app.models.Importer` which
    provides the platform persistent attributes for an importer object. Plugin authors can add
    additional persistent importer data by subclassing this object and adding Django fields. We
    defer to the Django docs on extending this model definition with additional fields.

    Validation is done the Django way, so custom validation can also be added the same as any
    Django model. We defer to the Django docs on adding custom validation to the subclassed
    importer. If any of the model validation methods are overridden, be sure to call super() so the
    platform can still perform its validation.

    Instantiation and calling of the subclassed plugin Importer is described in detail in the
    :meth: `Importer.sync` method.
    """

    def sync(self):
        """
        Perform a sync

        It is expected that plugins wanting to support sync will provide an implementation on the
        subclassed Importer.

        The model attributes encapsulate all of the information required to sync. This includes the
        platform :class: `pulp.app.models.Importer` base attributes and any custom attributes
        defined by the subclass.

        The model attributes were loaded from the database and then had the user specified override
        config applied on top. Additionally the importer is read-only and prevents the saving of
        changes to the Importer instance.

        Instantiation and calling of the sync method by the platform is roughly done with the
        following:

            1. The plugin provides an implementation called WidgetImporter which subclasses Importer

            2. The user makes a call to sync widget_importer (say id=10) with some override config

            3. The platform loads the saved
                >>> wi = WidgetImporter.objects.get(id=10)

            4. The platform puts the WidgetImporter into read-only mode

            5. The override config values are written over the in memory WidgetImporter

            6. Call the full_clean() method on the Django model for validation

                >>> wi.full_clean()

            7. Call into the sync method

                >>> wi.sync()

        Subclasses are designed to override this default implementation and should not call super().
        """
        raise NotImplementedError()

    def get_artifact_download(self, artifact, url, destination):
        """
        Build an artifact download object.

        Args:
            artifact (Artifact): The associated artifact.
            url (str): The download URL.
            destination (str): The absolute path to where the downloaded file is to be stored.

        Returns:
            pulp3.download.Download: The appropriate download.
        """
        download = HttpDownload(url, destination)
        download.ssl_ca_certificate = self.ssl_ca_certificate
        download.ssl_client_certificate = self.ssl_client_certificate
        download.ssl_client_key = self.ssl_client_key
        download.proxy_url = self.proxy_url
        download.headers = self.headers
        if artifact.size:
            validation = SizeValidation(artifact.size)
            download.validations.append(validation)
        for algorithm in DigestValidation.ALGORITHMS:
            try:
                digest = getattr(artifact, algorithm)
                if not digest:
                    continue
            except AttributeError:
                continue
            else:
                validation = DigestValidation(algorithm, digest)
                download.validations.append(validation)
                break
        return download
