from gettext import gettext as _
from urllib.parse import urlparse

from pulpcore.download import (DigestValidation, HttpDownload, FileDownload, FileWriter,
                               SizeValidation)
from pulpcore.app.upload import PulpTemporaryUploadedFile


class Factory:
    """
    Factory for creating download object based on URL scheme.

    Attributes:
        importer (pulpcore.plugin.models.Importer): An importer.

    Examples:
        >>>
        >>> importer = ..
        >>> url = ..
        >>> artifact = ..
        >>> download = Factory(importer).build(url, artifact=artifact)
        >>>
    """

    def __init__(self, importer):
        """

        Args:
            importer (pulpcore.plugin.models.Importer): An importer.
        """
        self.importer = importer

    def build(self, url, path=None, remote_artifact=None):
        """
        Build a downloader.

        Args:
            url (str): The download URL.
            path (str): The optional absolute path to where the downloaded file is to be stored.
            remote_artifact (pulpcore.app.models.RemoteArtifact): An optional remote artifact.

        Returns:
            pulpcore.download.Download: A download object configured using the
                attributes of the importer.
        """
        if (not path) and (not remote_artifact):
            raise ValueError(_('Either "path" or "artifact" is required.'))

        try:
            builder = Factory.BUILDER[urlparse(url).scheme.lower()]
        except KeyError:
            raise ValueError(_('URL: {u} not supported.'.format(u=url)))
        else:
            return builder(self, url, path, remote_artifact)

    def _file(self, url, path=None, artifact=None):
        """
        Build a download for file:// URLs.

        Args:
            url (str): The download URL.
            path (str): The optional absolute path to where the downloaded file is to be stored.
            artifact (pulpcore.app.models.Artifact): An optional artifact.

        Returns:
            FileDownload:
        """
        if artifact:
            _path = artifact.relative_path
        else:
            _path = path
        download = FileDownload(url, FileWriter(_path))
        self._add_validation(download, artifact)
        return download

    def _http(self, url, path=None, remote_artifact=None):
        """
        Build a download for http:// URLs.

        Args:
            url (str): The download URL.
            path (str): The optional absolute path to where the downloaded file is to be stored.
            artifact (pulpcore.app.models.Artifact): An optional artifact.

        Returns:
            HttpDownload: An http download.
        """
        if remote_artifact:
            import os
            _path = os.path.join("/var/lib/pulp/tmp", remote_artifact.sha256)
        else:
            _path = path
        download = HttpDownload(url, FileWriter(_path))
        download.user.name = self.importer.basic_auth_user
        download.user.password = self.importer.basic_auth_password
        self._add_validation(download, remote_artifact)
        return download

    def _https(self, url, path=None, remote_artifact=None):
        """
        Build a download for https:// URLs.

        Args:
            url (str): The download URL.
            path (str): The optional absolute path to where the downloaded file is to be stored.
            artifact (pulpcore.app.models.Artifact): An optional artifact.

        Returns:
            HttpDownload: An https download.
        """
        if remote_artifact:
            import os
            _path = os.path.join("/var/lib/pulp/tmp", remote_artifact.sha256)
        else:
            _path = path
        download = HttpDownload(url, FileWriter(_path))
        download.ssl.ca_certificate = self.importer.ssl_ca_certificate.name
        download.ssl.client_certificate = self.importer.ssl_client_certificate.name
        download.ssl.client_key = self.importer.ssl_client_key.name
        download.ssl.validation = self.importer.ssl_validation
        download.user.name = self.importer.basic_auth_user
        download.user.password = self.importer.basic_auth_password
        download.proxy_url = self.importer.proxy_url
        return download

    def _add_validation(self, download, artifact):
        """
        Add validations based on the artifact.

        Args:
            download (pulpcore.download.Download): A download object.
            artifact (pulpcore.app.models.Artifact): A content artifact.
        """
        if not artifact:
            return
        if not self.importer.validate:
            return
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

    # Map URLs scheme to builder method.
    BUILDER = {
        'file': _file,
        'http': _http,
        'https': _https,
    }
