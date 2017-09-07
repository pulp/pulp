import os

from gettext import gettext as _
from logging import getLogger, DEBUG

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseNotFound, StreamingHttpResponse
from django.views.generic import View

from wsgiref.util import FileWrapper

from pulpcore.app.models import Distribution


log = getLogger(__name__)
log.level = DEBUG


class ContentView(View):
    """
    Content endpoint.

    URL matching algorithm.

    http://redhat.com/content/cdn/stage/files/manifest
                              |-------------||--------|
                                     (1)          (2)

    1. Match: Distribution.base_path
    2. Match: PublishedFile.relative_path
    """

    BASE_PATH = 'content'

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

    def _match_distribution(self, path):
        """
        Match a distribution using a list of base paths.

        Args:
            path (str): The path component of the URL.

        Returns:
            Distribution: The matched distribution.

        Raises:
            ObjectDoesNotExist: when not matched.
        """
        base_paths = self._base_paths(path)
        try:
            return Distribution.objects.get(base_path__in=base_paths)
        except ObjectDoesNotExist:
            log.debug(
                _('Distribution not matched for %(path)s using: %(base_paths)s'),
                {
                    'path': path,
                    'base_paths': base_paths
                })
            raise

    def _match(self, path):
        """
        Match either a PublishedArtifact or PublishedMetadata.

        Args:
            path (str): The path component of the URL.

        Returns:
            str: The storage path of the matched object.

        Raises:
            ObjectDoesNotExist: The referenced object does not exist.

        """
        distribution = self._match_distribution(path)
        publication = distribution.publication
        if not publication:
            raise ObjectDoesNotExist()
        rel_path = path.lstrip('/')
        rel_path = rel_path[len(distribution.base_path):]
        rel_path = rel_path.lstrip('/')
        # artifact
        try:
            pa = publication.published_artifact.get(relative_path=rel_path)
        except ObjectDoesNotExist:
            pass
        else:
            artifact = pa.content_artifact.artifact
            if artifact.file:
                return artifact.file.name
            else:
                raise ObjectDoesNotExist()
        # metadata
        pm = publication.published_metadata.get(relative_path=rel_path)
        if pm.file:
            return pm.file.name
        else:
            raise ObjectDoesNotExist()

    @staticmethod
    def _stream(storage_path):
        """
        Get streaming response.

        Args:
            storage_path (str): The storage path of the requested object.

        Returns:
            HttpResponse: Always.

        """
        try:
            file = FileWrapper(open(storage_path, 'rb'))
        except FileNotFoundError:
            return HttpResponseNotFound()
        response = StreamingHttpResponse(file)
        response['Content-Length'] = os.path.getsize(storage_path)
        response['Content-Disposition'] = \
            'attachment; filename={n}'.format(n=os.path.basename(storage_path))
        return response

    @staticmethod
    def _redirect(storage_path):
        """
        Redirect to streamer.

        Args:
            storage_path (str): The storage path of the requested object.

        Returns:

        """
        # :TODO:

    @staticmethod
    def _xsend(storage_path):
        """
        Stream using X-SEND.

        Args:
            storage_path (str): The storage path of the requested object.

        Returns:

        """
        # :TODO:

    def get(self, request):
        """
        Get content artifact (bits).

        Args:
            request (django.http.HttpRequest): A request for a content artifact.

        Returns:
            django.http.StreamingHttpResponse: on found.
            django.http.HttpResponseNotFound: on not-found.

        """
        try:
            path = request.path.strip('/')
            path = path[len(self.BASE_PATH):]
            storage_path = self._match(path)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()

        # TODO: Eventually, choose _redirect() and _xsend() as appropriate.
        return self._stream(storage_path)
