import os

from gettext import gettext as _
from logging import getLogger, DEBUG

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseForbidden,
    HttpResponseNotFound,
    StreamingHttpResponse)
from django.views.generic import View

from wsgiref.util import FileWrapper

from pulpcore.app.models import Distribution, ContentArtifact


log = getLogger(__name__)
log.level = DEBUG


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


class ContentView(View):
    """
    Content endpoint.

    URL matching algorithm.

    http://redhat.com/content/cdn/stage/files/manifest
                              |-------------||--------|
                                     (1)        (2-4)

    1. Match: Distribution.base_path
    2. Match: PublishedArtifact.relative_path
    3. Match: PublishedMetadata.relative_path
    4. Match: ContentArtifact.relative_path (pass-through publications only).
    """

    BASE_PATH = 'pulp/content'

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

    def _published_path(self, request):
        """
        Get the path of the (requested) published object.

        The leading and trailing '/' are stripped. Then the BASE_PATH prefix is stripped.

        Args:
            request (django.http.HttpRequest): A request for a content artifact.

        Returns:
            str: The path of the (requested) published object.
        """
        path = request.path.strip('/')
        path = path[len(self.BASE_PATH):]
        return path.lstrip('/')

    def _match_distribution(self, path):
        """
        Match a distribution using a list of base paths.

        Args:
            path (str): The path component of the URL.

        Returns:
            Distribution: The matched distribution.

        Raises:
            PathNotResolved: when not matched.
        """
        base_paths = self._base_paths(path)
        try:
            return Distribution.objects.get(base_path__in=base_paths)
        except ObjectDoesNotExist:
            log.debug(_('Distribution not matched for {path} using: {base_paths}').format(
                path=path, base_paths=base_paths
            ))
            raise PathNotResolved(path)

    def _match(self, path):
        """
        Match either a PublishedArtifact or PublishedMetadata.

        Args:
            path (str): The path component of the URL.

        Returns:
            str: The storage path of the matched object.

        Raises:
            PathNotResolved: The path could not be matched to a published file.
            ArtifactNotFound: The published-artifact was matched but the
                associated artifact does not exist.

        """
        distribution = self._match_distribution(path)
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
            artifact = pa.content_artifact.artifact
            if artifact:
                return artifact.file.name
            else:
                raise ArtifactNotFound(path)

        # published metadata
        try:
            pm = publication.published_metadata.get(relative_path=rel_path)
        except ObjectDoesNotExist:
            pass
        else:
            return pm.file.name

        # pass-through
        if publication.pass_through:
            try:
                ca = ContentArtifact.objects.get(
                    content__in=publication.repository_version.content,
                    relative_path=rel_path)
            except MultipleObjectsReturned:
                log.debug(
                    _('Multiple (pass-through) matches for {b}/{p}'),
                    {
                        'b': distribution.base_path,
                        'p': rel_path,
                    }
                )
            except ObjectDoesNotExist:
                pass
            else:
                artifact = ca.artifact
                if artifact:
                    return artifact.file.name
                else:
                    raise ArtifactNotFound(path)

        raise PathNotResolved(path)

    def _django(self, path):
        """
        The content web server is Django.

        Stream the bits.

        Args:
            path (str): The fully qualified path to the file to be served.

        Returns:
            StreamingHttpResponse: Stream the requested content.

        """
        try:
            file = FileWrapper(open(path, 'rb'))
        except FileNotFoundError:
            return HttpResponseNotFound()
        except PermissionError:
            return HttpResponseForbidden()
        response = StreamingHttpResponse(file)
        response['Content-Length'] = os.path.getsize(path)
        return response

    def _apache(self, path):
        """
        The content web server is Apache.

        Args:
            path (str): The fully qualified path to the file to be served.

        Returns:
            HttpResponse: A response with X-SENDFILE header.
        """
        response = HttpResponse()
        response['X-SENDFILE'] = path
        return response

    def _nginx(self, path):
        """
        The content web server is NGINX.

        Args:
            path (str): The fully qualified path to the file to be served.

        Returns:
            HttpResponse: A response with X-Accel-Redirect header.
        """
        response = HttpResponse()
        response['X-Accel-Redirect'] = path
        return response

    def _redirect(self, request):
        """
        Get redirect-to-streamer response.

        Args:
            request (django.http.HttpRequest): A request for a published file.

        Returns:
            HttpResponseRedirect: Redirect to streamer.
        """
        redirect = settings.CONTENT['REDIRECT']

        enabled = redirect['ENABLED']
        host = redirect['HOST'] or request.get_host().split(':')[0]
        port = redirect['PORT'] or request.get_port()
        prefix = redirect['PATH_PREFIX']

        if not enabled:
            return HttpResponseNotFound()

        path = os.path.join(
            prefix.strip('/'),
            self._published_path(request)
        )

        url = '{scheme}://{host}:{port}/{path}'.format(
            scheme=request.scheme,
            host=host,
            path=path,
            port=port)

        log.debug(_('Redirected: %(u)s'), {'u': url})
        response = HttpResponseRedirect(url)
        return response

    def _dispatch(self, request, path):
        """
        Dispatch to the appropriate responder (method).

        Args:
            request (django.http.HttpRequest): A request for a published file.
            path (str): The fully qualified path to the file to be served.

        Returns:
            django.http.StreamingHttpResponse: on found.
            django.http.HttpResponseNotFound: on not-found.
            django.http.HttpResponseForbidden: on forbidden.
            django.http.HttpResponseRedirect: on redirect to the streamer.
        """
        server = settings.CONTENT['WEB_SERVER']

        try:
            responder = self.RESPONDER[server]
        except KeyError:
            raise ValueError(_('Web server "{t}" not supported.').format(t=server))
        else:
            disposition = os.path.basename(request.path)
            response = responder(self, path)
            response['Content-Disposition'] = 'attachment; filename={n}'.format(n=disposition)
            return response

    def get(self, request):
        """
        Get content artifact (bits).

        Args:
            request (django.http.HttpRequest): A request for a published file.

        Returns:
            django.http.StreamingHttpResponse: on found.
            django.http.HttpResponseNotFound: on not-found.
            django.http.HttpResponseForbidden: on forbidden.
            django.http.HttpResponseRedirect: on redirect to the streamer.
        """
        try:
            path = self._published_path(request)
            storage_path = self._match(path)
        except PathNotResolved:
            return HttpResponseNotFound()
        except ArtifactNotFound:
            return self._redirect(request)
        else:
            return self._dispatch(request, storage_path)

    # Mapping of responder-method based on the type of web server.
    RESPONDER = {
        'django': _django,
        'apache': _apache,
        'nginx': _nginx,
    }
