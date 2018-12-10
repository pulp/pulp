from gettext import gettext as _
import logging
import os

# https://github.com/rochacbruno/dynaconf/issues/89
from dynaconf.contrib import django_dynaconf  # noqa

import django  # noqa otherwise E402: module level not at top of file
django.setup()  # noqa otherwise E402: module level not at top of file

from aiohttp import web
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import transaction
from pulpcore.app.models import Artifact, ContentArtifact, Distribution, Remote


log = logging.getLogger(__name__)


class PathNotResolved(Exception):
    """
    The path could not be resolved to a published file.

    This could be caused by either the distribution, the publication,
    or the published file could not be found.
    """
    pass


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
            request (:class:`django.http.HttpRequest`): A request for a published file.
            distribution (:class:`pulpcore.plugin.models.Distribution`): The matched distribution.

        Raises:
            PermissionError: When not permitted.
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
            raise
        except Exception:
            reason = _('Guard "{g}" failed:').format(g=guard.name)
            log.debug(reason, exc_info=True)
            raise PermissionError(reason)

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
        Handler._permit(request, distribution)
        publication = distribution.publication
        if not publication:
            raise PathNotResolved(path)
        rel_path = path.lstrip('/')
        rel_path = rel_path[len(distribution.base_path):]
        rel_path = rel_path.lstrip('/')

        # published artifact
        try:
            pa = publication.published_artifact.get(relative_path=rel_path)
        except ObjectDoesNotExist:
            pass
        else:
            return web.FileResponse(pa.content_artifact.artifact.file.name)

        # published metadata
        try:
            pm = publication.published_metadata.get(relative_path=rel_path)
        except ObjectDoesNotExist:
            pass
        else:
            return web.FileResponse(pm.file.name)

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
                    return web.FileResponse(ca.artifact.file.name)
                else:
                    return await self._stream_content_artifact(request, web.StreamResponse(), ca)
        else:
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
            with transaction.atomic():
                new_artifact = Artifact(
                    **download_result.artifact_attributes,
                    file=download_result.path
                )
                new_artifact.save()
                content_artifact.artifact = new_artifact
                content_artifact.save()
        await response.write_eof()
        return response
