from gettext import gettext as _
import logging
import os

# https://github.com/rochacbruno/dynaconf/issues/89
from dynaconf.contrib import django_dynaconf  # noqa

import django  # noqa otherwise E402: module level not at top of file
django.setup()  # noqa otherwise E402: module level not at top of file

from aiohttp.web import FileResponse, StreamResponse
from aiohttp.web_exceptions import HTTPForbidden, HTTPFound, HTTPNotFound
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import IntegrityError, transaction
from pulpcore.app.models import Artifact, ContentArtifact, Distribution, Remote


log = logging.getLogger(__name__)


class PathNotResolved(HTTPNotFound):
    """
    The path could not be resolved to a published file.

    This could be caused by either the distribution, the publication,
    or the published file could not be found.
    """

    def __init__(self, path, *args, **kwargs):
        """Initialize the Exception."""
        self.path = path
        super().__init__(*args, **kwargs)


class ArtifactNotFound(Exception):
    """
    The artifact associated with a published-artifact does not exist.
    """
    pass


HOP_BY_HOP_HEADERS = [
    'connection',
    'keep-alive',
    'public',
    'proxy-authenticate',
    'transfer-encoding',
    'upgrade',
]


class Handler:

    async def stream_content(self, request):
        """
        The request handler for the Content app.

        Args:
            request (:class:`aiohttp.web.request`): The request from the client.

        Returns:
            :class:`aiohttp.web.StreamResponse` or :class:`aiohttp.web.FileResponse`: The response
                back to the client.
        """
        path = request.match_info['path']
        return await self._match_and_stream(path, request)

    @staticmethod
    def _base_paths(path):
        """
        Get a list of base paths used to match a distribution.

        Args:
            path (str): The path component of the URL.

        Returns:
            list: Of base paths.

        """
        tree = []
        while True:
            base = os.path.split(path.strip('/'))[0]
            if not base:
                break
            tree.append(base)
            path = base
        return tree

    @staticmethod
    def _match_distribution(path):
        """
        Match a distribution using a list of base paths.

        Args:
            path (str): The path component of the URL.

        Returns:
            Distribution: The matched distribution.

        Raises:
            PathNotResolved: when not matched.
        """
        base_paths = Handler._base_paths(path)
        try:
            return Distribution.objects.get(base_path__in=base_paths)
        except ObjectDoesNotExist:
            log.debug(_('Distribution not matched for {path} using: {base_paths}').format(
                path=path, base_paths=base_paths
            ))
            raise PathNotResolved(path)

    @staticmethod
    def _permit(request, distribution):
        """
        Permit the request.

        Authorization is delegated to the optional content-guard associated with the distribution.

        Args:
            request (:class:`aiohttp.web.Request`): A request for a published file.
            distribution (:class:`pulpcore.plugin.models.Distribution`): The matched distribution.

        Raises:
            :class:`aiohttp.web_exceptions.HTTPForbidden`: When not permitted.
        """
        guard = distribution.content_guard
        if not guard:
            return
        try:
            guard.cast().permit(request)
        except PermissionError as pe:
            log.debug(
                _('Path: %(p)s not permitted by guard: "%(g)s" reason: %(r)s'),
                {
                    'p': request.path,
                    'g': guard.name,
                    'r': str(pe)
                })
            raise HTTPForbidden(reason=str(pe))
        except Exception:
            reason = _('Guard "{g}" failed:').format(g=guard.name)
            log.debug(reason, exc_info=True)
            raise HTTPForbidden(reason=reason)

    async def _match_and_stream(self, path, request):
        """
        Match the path and stream results either from the filesystem or by downloading new data.

        Args:
            path (str): The path component of the URL.
            request(:class:`~aiohttp.web.Request`): The request to prepare a response for.

        Raises:
            PathNotResolved: The path could not be matched to a published file.
            PermissionError: When not permitted.

        Returns:
            :class:`aiohttp.web.StreamResponse` or :class:`aiohttp.web.FileResponse`: The response
                streamed back to the client.
        """
        distribution = Handler._match_distribution(path)
        self._permit(request, distribution)
        publication = distribution.publication
        if not publication:
            raise PathNotResolved(path)
        rel_path = path.lstrip('/')
        rel_path = rel_path[len(distribution.base_path):]
        rel_path = rel_path.lstrip('/')

        # published artifact
        try:
            pa = publication.published_artifact.get(relative_path=rel_path)
            ca = pa.content_artifact
        except ObjectDoesNotExist:
            pass
        else:
            if ca.artifact:
                return self._handle_file_response(ca.artifact.file)
            else:
                return await self._stream_content_artifact(request, StreamResponse(), ca)

        # published metadata
        try:
            pm = publication.published_metadata.get(relative_path=rel_path)
        except ObjectDoesNotExist:
            pass
        else:
            return self.handle_file_response(pm.file)

        # pass-through
        if publication.pass_through:
            try:
                ca = ContentArtifact.objects.get(
                    content__in=publication.repository_version.content,
                    relative_path=rel_path)
            except MultipleObjectsReturned:
                log.error(
                    _('Multiple (pass-through) matches for {b}/{p}'),
                    {
                        'b': distribution.base_path,
                        'p': rel_path,
                    }
                )
                raise
            except ObjectDoesNotExist:
                pass
            else:
                if ca.artifact:
                    return self._handle_file_response(ca.artifact.file)
                else:
                    return await self._stream_content_artifact(request, StreamResponse(), ca)
        raise PathNotResolved(path)

    async def _stream_content_artifact(self, request, response, content_artifact):
        """
        Stream and optionally save a ContentArtifact by requesting it using the associated remote.

        Args:
            request(:class:`~aiohttp.web.Request`): The request to prepare a response for.
            response (:class:`~aiohttp.web.StreamResponse`): The response to stream data to.
            content_artifact (:class:`~pulpcore.plugin.models.ContentArtifact`): The ContentArtifact
                to fetch and then stream back to the client
        """
        remote_artifact = content_artifact.remoteartifact_set.get()
        remote = remote_artifact.remote.cast()

        async def handle_headers(headers):
            for name, value in headers.items():
                if name.lower() in HOP_BY_HOP_HEADERS:
                    continue
                response.headers[name] = value
            await response.prepare(request)

        async def handle_data(data):
            await response.write(data)
            if remote.policy != Remote.STREAMED:
                await original_handle_data(data)

        async def finalize():
            if remote.policy != Remote.STREAMED:
                await original_finalize()

        downloader = remote.get_downloader(remote_artifact=remote_artifact,
                                           headers_ready_callback=handle_headers)
        original_handle_data = downloader.handle_data
        downloader.handle_data = handle_data
        original_finalize = downloader.finalize
        downloader.finalize = finalize
        download_result = await downloader.run()
        if remote.policy != Remote.STREAMED:
            self._save_content_artifact(download_result, content_artifact)
        await response.write_eof()
        return response

    def _save_content_artifact(self, download_result, content_artifact):
        """
        Create/Get an Artifact and associate it to a ContentArtifact.

        Create (or get if already existing) an :class:`~pulpcore.plugin.models.Artifact`
        based on the `download_result` and associate it to the given `content_artifact`. Both
        the created artifact and the updated content_artifact are saved to the DB.

        Plugin-writers may overide this method if their content module requires
        additional/different steps for saving.

        Args:
            download_result (:class:`~pulpcore.plugin.download.DownloadResult`: The
                DownloadResult for the downloaded artifact.

            content_artifact (:class:`~pulpcore.plugin.models.ContentArtifact`): The
                ContentArtifact to associate the Artifact with.

        Returns:
            The associated :class:`~pulpcore.plugin.models.Artifact`.
        """
        artifact = Artifact(
            **download_result.artifact_attributes,
            file=download_result.path
        )
        with transaction.atomic():
            try:
                with transaction.atomic():
                    artifact.save()
            except IntegrityError:
                artifact = Artifact.objects.get(artifact.q())
            content_artifact.artifact = artifact
            content_artifact.save()
        return artifact

    def _handle_file_response(self, file):
        """
        Handle response for file.

        Depending on where the file storage (e.g. filesystem, S3, etc) this could be responding with
        the file (filesystem) or a redirect (S3).

        Args:
            file (:class:`django.db.models.fields.files.FieldFile`): File to respond with

        Raises:
            :class:`aiohttp.web_exceptions.HTTPFound`: When we need to redirect to the file
            NotImplementedError: If file is stored in a file storage we can't handle

        Returns:
            The :class:`aiohttp.web.FileResponse` for the file.
        """
        if settings.DEFAULT_FILE_STORAGE == 'pulpcore.app.models.storage.FileSystem':
            return FileResponse(file.name)
        elif settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto3.S3Boto3Storage':
            raise HTTPFound(file.url)
        else:
            raise NotImplementedError()
