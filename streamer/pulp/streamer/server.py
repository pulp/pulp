import logging

from gettext import gettext as _
from httplib import NOT_FOUND, INTERNAL_SERVER_ERROR
from urlparse import urlparse

from mongoengine import DoesNotExist, NotUniqueError
from nectar.listener import AggregatingEventListener
from requests import Session
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from pulp.plugins.loader import api as plugin_api
from pulp.server.constants import PULP_STREAM_REQUEST_HEADER
from pulp.server.content.sources.container import ContentContainer
from pulp.server.content.sources.model import Request as ContainerRequest
from pulp.server.db.model import DeferredDownload, LazyCatalogEntry
from pulp.server.controllers import repository as repo_controller
from pulp.plugins.loader.exceptions import PluginNotFound
from pulp.streamer import adapters as pulp_adapters

logger = logging.getLogger(__name__)

# These HTTP/1.1 headers are defined as being hop-by-hop and should
# not be passed back to clients. All other headers defined by
# HTTP/1.1 are end-to-end headers and should be passed back to the
# client. See RFC 2068, section 13.5.1 for more information.
#
# Headers are lowercase since `lower` is called in the nectar-provided
# headers when checking to see if they're in this list. Twisted also
# returns all its headers with `lower` called on them, so this is for
# consistency reasons only.
HOP_BY_HOP_HEADERS = [
    'connection',
    'keep-alive',
    'public',
    'proxy-authenticate',
    'transfer-encoding',
    'upgrade',
]


class DownloadFailed(Exception):
    """
    Download failed.
    """


class DownloadListener(AggregatingEventListener):
    """
    Nectar download listener.
    """

    def __init__(self, streamer, request):
        """
        :param streamer: The streamer.
        :type  streamer: Streamer
        :param request: The original twisted client HTTP request being handled by the streamer.
        :type  request: twisted.web.server.Request
        """
        super(DownloadListener, self).__init__()
        self.streamer = streamer
        self.request = request

    def download_headers(self, report):
        """
        Forward response headers to the original client HTTP request.
        This includes adding the cache-control header with the max-age
        which is loaded from the configuration.

        :param report: The download report.
        :type  report: nectar.report.DownloadReport
        """
        super(DownloadListener, self).download_headers(report)
        # forward
        for key, value in report.headers.items():
            if key.lower() not in HOP_BY_HOP_HEADERS:
                self.request.setHeader(key, value)
        # additions
        max_age = self.streamer.config.get('streamer', 'cache_timeout')
        cache_control = 'public, s-maxage={m}, max-age={m}'.format(m=max_age)
        self.request.setHeader('Cache-Control', cache_control)

    def download_failed(self, report):
        """
        Log download failures.

        :param report: The download report.
        :type  report: nectar.report.DownloadReport
        """
        super(DownloadListener, self).download_failed(report)
        code = report.error_report.get('response_code', '')
        logger.info(_('Download failed [{code}]: {url}').format(code=code, url=report.url))


class Streamer(Resource):
    """
    Define the web resource that streams content from the upstream repository
    to the client.
    """

    # Ensure self.getChild isn't called as this has no child resources
    isLeaf = True

    def __init__(self, config):
        """
        Initialize a streamer instance.

        :param config: The configuration for this streamer instance.
        :type  config: ConfigParser.SafeConfigParser
        """
        Resource.__init__(self)
        self.config = config
        # Used to pool TCP connections for upstream requests. Once requests #2863 is
        # fixed and available, remove the PulpHTTPAdapter. This is a short-term work-around
        # to avoid carrying the package.
        self.session = Session()
        self.session.mount('https://', pulp_adapters.PulpHTTPAdapter())

    def render_GET(self, request):
        """
        Handle GET requests to this web resource.

        This method performs the following tasks to service the request:

            * The requested URL is checked to ensure it has a valid signature
              from the Pulp server.
            * The unit specified by the request is looked up in the Pulp unit
              catalog and the correct downloader is retrieved based on the specific
              file requested.
            * The file is downloaded using the Nectar downloader and the content
              is streamed to the client as it is received.

        :param request: The original twisted client HTTP request being handled by the streamer.
        :type  request: twisted.web.server.Request
        """
        reactor.callInThread(self._handle_get, request)
        return NOT_DONE_YET

    def _handle_get(self, request):
        """
        Download the requested content using the content unit catalog and dispatch
        a celery task that causes Pulp to download the newly cached unit.

        :param request: The original twisted client HTTP request being handled by the streamer.
        :type  request: twisted.web.server.Request
        """
        with Responder(request) as responder:
            try:
                path = urlparse(request.uri).path
                q_set = LazyCatalogEntry.objects.filter(path=path)
                q_set = q_set.order_by('-_id', '-revision')
                count = q_set.count()
                if not count:
                    logger.error(_('No catalog entry found. path={p}'.format(p=path)))
                    request.setResponseCode(NOT_FOUND)
                    return
                for entry in q_set.all():
                    logger.info('Trying URL: {url}'.format(url=entry.url))
                    try:
                        last_report = self._download(request, entry, responder)
                        self._on_succeeded(entry, request, last_report)
                        return
                    except (DownloadFailed, DoesNotExist, PluginNotFound):
                        # try another
                        continue
                # Failed
                self._on_all_failed(request)
            except Exception:
                logger.exception(_('An unexpected error occurred: {url}').format(url=request.uri))
                request.setResponseCode(INTERNAL_SERVER_ERROR)
                request.setHeader('Content-Length', '0')

    def _on_succeeded(self, entry, request, report):
        """
        The download succeeded.

        :param entry: A catalog entry.
        :type  entry: LazyCatalogEntry
        :param request: An HTTP request.
        :type  request: twisted.web.server.Request
        :param report: A download report.
        :type  report: nectar.report.DownloadReport
        """
        pulp_requested = request.getHeader(PULP_STREAM_REQUEST_HEADER)
        if not pulp_requested:
            self._insert_deferred(entry)

    @staticmethod
    def _on_all_failed(request):
        """
        All downloads failed.

        :param request: The original twisted client HTTP request being handled by the streamer.
        :type  request: twisted.web.server.Request
        """
        logger.error(_('All download attempts failed: {url}').format(url=request.uri))
        request.setHeader('Content-Length', '0')
        request.setResponseCode(NOT_FOUND)

    def _download(self, request, entry, responder):
        """
        Download the file.

        :param request: The original twisted client HTTP request being handled by the streamer.
        :type  request: twisted.web.server.Request
        :param entry: The catalog entry to download.
        :type  entry: pulp.server.db.model.LazyCatalogEntry
        :param responder: The file-like object that nectar should write to.
        :type  responder: Responder
        :return: The download report.
        :rtype: nectar.report.DownloadReport
        """
        downloader = None

        try:
            unit = self._get_unit(entry)
            downloader = self._get_downloader(request, entry)
            alt_request = ContainerRequest(
                entry.unit_type_id,
                unit.unit_key,
                entry.url,
                responder)
            listener = downloader.event_listener
            container = ContentContainer(threaded=False)
            container.download(downloader, [alt_request], listener)
            if listener.succeeded_reports:
                return listener.succeeded_reports[0]
            else:
                raise DownloadFailed()
        finally:
            try:
                downloader.config.finalize()
            except Exception:
                # ignored.
                pass

    def _get_downloader(self, request, entry):
        """
        Get the configured downloader.

        :param request: The original twisted client HTTP request being handled by the streamer.
        :type  request: twisted.web.server.Request
        :param entry: A catalog entry.
        :type  entry: LazyCatalogEntry
        :return: The configured downloader.
        :rtype:  nectar.downloaders.base.Downloader
        :raise: PluginNotFound: when plugin not found.
        :raise: DoesNotExist: when importer not found.
        """
        try:
            importer, config, model = \
                repo_controller.get_importer_by_id(entry.importer_id)
            model.config = config.flatten()
            downloader = importer.get_downloader_for_db_importer(
                model, entry.url, working_dir='/tmp')
            listener = DownloadListener(self, request)
            downloader.event_listener = listener
            downloader.session = self.session
            return downloader
        except (PluginNotFound, DoesNotExist):
            msg = _('Plugin not-found: referenced by catalog entry for {path}')
            logger.error(msg.format(path=entry.path))
            raise

    @staticmethod
    def _get_unit(entry):
        """
        Get the content unit referenced by the catalog entry.

        :param entry: A catalog entry.
        :type  entry: LazyCatalogEntry
        :return: The unit.
        :raises DoesNotExist: when not found.
        """
        try:
            model = plugin_api.get_unit_model_by_id(entry.unit_type_id)
            q_set = model.objects.filter(id=entry.unit_id)
            q_set = q_set.only(*model.unit_key_fields)
            return q_set.get()
        except DoesNotExist:
            msg = _('The catalog entry for {path} references unknown unit: {unit_type}:{id}')
            logger.error(msg.format(
                path=entry.path,
                unit_type=entry.unit_type_id,
                id=entry.unit_id))
            raise

    @staticmethod
    def _insert_deferred(entry):
        """
        Request deferred download.
        Add deferred download record for background processing.

        :param entry: A catalog entry.
        :type  entry: LazyCatalogEntry
        """
        try:
            model = DeferredDownload(
                unit_id=entry.unit_id,
                unit_type_id=entry.unit_type_id)
            model.save()
        except NotUniqueError:
            # There's already an entry for this unit.
            pass


class Responder(object):
    """
    This class provides an object that can be provided to Nectar instead of a
    file which forwards all write calls to the Twisted Request.
    """

    def __init__(self, request):
        """
        Initialize a new Responder.

        :param request: The original twisted client HTTP request being handled by the streamer.
        :type  request: twisted.web.server.Request
        """
        self.request = request

    def __enter__(self):
        """
        Support 'with' keyword.

        :return: The instance of the class.
        :rtype:  Responder
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Closes the Responder, which invokes the
        twisted.web.server.Request.finish method

        :param exc_type: The exception type, if any.
        :type  exc_type: type.TypeType
        :param exc_value: The exception instance, if any.
        :type  exc_value: Exception
        :param traceback: The traceback of the exception, if any.
        :type  traceback: traceback
        :return: False so exception is re-raised.
        :rtype: bool
        """
        self.close()
        return False

    def close(self):
        """
        Forward the call to close the 'file' to the request.finish method.
        """
        reactor.callFromThread(self.finish)

    def finish(self):
        """
        Handles RuntimeErrors raised by calling ``finish`` on a request after
        the connection is closed.

        If finish is called after the client disconnects, a RuntimeError is
        raised and Twisted logs the stack trace. Clients disconnecting before
        Twisted gets around to calling ``finish`` is not uncommon. Ultimately
        there should be a handler that stops streaming if the client disconnects,
        but that is tricky with the current implementation's use of threads.
        """
        try:
            self.request.finish()
        except RuntimeError as e:
            logger.debug(str(e))

    def write(self, data):
        """
        Forward the data to the request.write method, which writes data to
        the transport (if not responding to a HEAD request).

        :param data: A string to write to the response.
        :type  data: str
        """
        reactor.callFromThread(self.request.write, data)
