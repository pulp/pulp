from gettext import gettext as _

from pulpcore.app.models import Artifact as PlatformArtifact
from pulpcore.app.models import Remote as PlatformRemote

from pulpcore.plugin.download import DownloaderFactory


class Remote(PlatformRemote):
    """
    The base settings used to sync content.

    This is meant to be subclassed by plugin authors as an opportunity to provide plugin-specific
    persistent data attributes for a plugin remote subclass.

    This object is a Django model that inherits from :class: `pulpcore.app.models.Remote` which
    provides the platform persistent attributes for a remote object. Plugin authors can add
    additional persistent remote data by subclassing this object and adding Django fields. We
    defer to the Django docs on extending this model definition with additional fields.

    Validation of the remote is done at the API level by a plugin defined subclass of
    :class: `pulpcore.plugin.serializers.repository.RemoteSerializer`.
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
                get_downloader().
        """
        try:
            return self._download_factory
        except AttributeError:
            self._download_factory = DownloaderFactory(self)
            return self._download_factory

    def get_downloader(self, remote_artifact=None, url=None, **kwargs):
        """
        Get a downloader from either a RemoteArtifact or URL that is configured with this Remote.

        This method accepts either `remote_artifact` or `url` but not both. At least one is
        required. If neither or both are passed a ValueError is raised.

        Plugin writers are expected to override when additional configuration is needed or when
        another class of download is required.

        Args:
            remote_artifact (:class:`~pulpcore.app.models.RemoteArtifact`): The RemoteArtifact to
                download.
            url (str): The URL to download.
            kwargs (dict): This accepts the parameters of
                :class:`~pulpcore.plugin.download.BaseDownloader`.

        Raises:
            ValueError: If neither remote_artifact and url are passed, or if both are passed.

        Returns:
            subclass of :class:`~pulpcore.plugin.download.BaseDownloader`: A downloader that
            is configured with the remote settings.
        """
        if remote_artifact and url:
            raise ValueError(_("get_downloader() cannot accept both 'remote_artifact' and 'url'."))
        if remote_artifact is None and url is None:
            raise ValueError(_("get_downloader() requires either 'remote_artifact' and 'url'."))
        if remote_artifact:
            url = remote_artifact.url
            expected_digests = {}
            for digest_name in PlatformArtifact.DIGEST_FIELDS:
                digest_value = getattr(remote_artifact, digest_name)
                if digest_value:
                    expected_digests[digest_name] = digest_value
            if expected_digests:
                kwargs['expected_digests'] = expected_digests
            if remote_artifact.size:
                kwargs['expected_size'] = remote_artifact.size
        return self.download_factory.build(url, **kwargs)
