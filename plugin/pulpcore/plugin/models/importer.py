from pulpcore.app.models import Importer as PlatformImporter

from pulpcore.plugin.download import DownloaderFactory


class Importer(PlatformImporter):
    """
    The base settings used to sync content.

    This is meant to be subclassed by plugin authors as an opportunity to provide plugin-specific
    persistent data attributes for a plugin importer subclass.

    This object is a Django model that inherits from :class: `pulpcore.app.models.Importer` which
    provides the platform persistent attributes for an importer object. Plugin authors can add
    additional persistent importer data by subclassing this object and adding Django fields. We
    defer to the Django docs on extending this model definition with additional fields.

    Validation of the importer is done at the API level by a plugin defined subclass of
    :class: `pulpcore.plugin.serializers.repository.ImporterSerializer`.
    """

    class Meta:
        abstract = True

    @property
    def download_factory(self):
        """
        Return the DownloaderFactory which can be used to generate asyncio capable downloaders.

        Upon first access, the DownloaderFactory is instantiated and saved internally.

        Plugin writers are expected to override when additional configuration of the
        DownloaderFactory is needed.

        Returns:
            DownloadFactory: The instantiated DownloaderFactory to be used by
                get_downloader()
        """
        try:
            return self._download_factory
        except AttributeError:
            self._download_factory = DownloaderFactory(self)
            return self._download_factory

    def get_downloader(self, url, **kwargs):
        """
        Get an asyncio capable downloader that is configured with the importer settings.

        Plugin writers are expected to override when additional configuration is needed or when
        another class of download is required.

        Args:
            url (str): The download URL.
            kwargs (dict): This accepts the parameters of
                :class:`~pulpcore.plugin.download.BaseDownloader`.

        Returns:
            subclass of :class:`~pulpcore.plugin.download.BaseDownloader`: A downloader that
            is configured with the importer settings.
        """
        return self.download_factory.build(url, **kwargs)
