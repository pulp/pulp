from gettext import gettext as _
from httplib import NOT_FOUND, INTERNAL_SERVER_ERROR, SERVICE_UNAVAILABLE
from urlparse import urlparse
import logging

from mongoengine import DoesNotExist, NotUniqueError
from nectar import listener as nectar_listener
import requests
from twisted.internet import reactor
from twisted.web import resource
from twisted.web.server import NOT_DONE_YET

from pulp.plugins.loader import api as plugins_api
from pulp.server.constants import PULP_STREAM_REQUEST_HEADER
from pulp.server.content.sources import container as content_container
from pulp.server.content.sources import model as content_models
from pulp.server.db import model
from pulp.server.controllers import repository as repo_controller
from pulp.plugins.loader.exceptions import PluginNotFound

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


class StreamerListener(nectar_listener.DownloadEventListener):
    """
    This DownloadEventListener subclass's purpose is to set the
    response headers on the given HTTP request. This includes setting
    the cache-control header with the max-age which is loaded from the
    streamer configuration file.
    """

    def __init__(self, request, streamer_config, catalog_entry, pulp_request=False):
        """
        Initialize a StreamerNectarListener.

        :param request:         the request to set the response headers for.
        :type  request:         twisted.web.server.Request
        :param streamer_config: The configuration for this streamer instance.
        :type  streamer_config: ConfigParser.SafeConfigParser
        :param catalog_entry:   Catalog entry for the file requested.
        :type  catalog_entry:   pulp.server.db.model.LazyCatalogEntry
        :param pulp_request:    True if this request originated from Pulp.
        :type  pulp_request:    bool
        """
        super(StreamerListener, self).__init__()
        self.request = request
        self.streamer_config = streamer_config
        self.catalog_entry = catalog_entry
        self.pulp_request = pulp_request

    def download_headers(self, report):
        """
        Forward a subset of the HTTP headers received from the upstream server as
        well as set the cache-control header to the value specified by the streamer
        configuration file. This header is used by clients to determine how to
        cache the response.

        :param report: The download report for this request.
        :type  report: nectar.report.DownloadReport
        """
        for header_key, header_value in report.headers.items():
            if header_key.lower() not in HOP_BY_HOP_HEADERS:
                self.request.setHeader(header_key, header_value)

        max_age = {'max_age': self.streamer_config.get('streamer', 'cache_timeout')}
        cache_header = 'public, s-maxage=%(max_age)s, max-age=%(max_age)s' % max_age
        self.request.setHeader('Cache-Control', cache_header)

    def download_failed(self, report):
        """
        Perform cleanup on failed downloads. Specifically, Nectar does not download
        any content if the server returns a non-200 code. This is problematic because
        it will return headers to the client which include a Content-Length that is
        likely not 0, since most servers provide pages detailing the problem that
        occurred.

        :param report: The download report for this request.
        :type  report: nectar.report.DownloadReport
        """
        # Currently Nectar returns headers with a content-length even
        # when it doesn't download anything.
        self.request.setHeader('Content-Length', '0')
        if 'response_code' in report.error_report:
            self.request.setResponseCode(report.error_report['response_code'])
        else:
            # Nectar doesn't give us a good way to know exactly went wrong; return
            # a generic HTTP 503 and hope Nectar logged enough to be useful
            self.request.setResponseCode(SERVICE_UNAVAILABLE)

    def download_succeeded(self, report):
        """
        If the download was successful, add a deferred download entry.

        :param report: The download report for this request.
        :type  report: nectar.report.DownloadReport
        """
        if not self.pulp_request:
            try:
                download = model.DeferredDownload(
                    unit_id=self.catalog_entry.unit_id,
                    unit_type_id=self.catalog_entry.unit_type_id
                )
                download.save()
            except NotUniqueError:
                # There's already an entry for this unit.
                pass


class Streamer(resource.Resource):
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
        resource.Resource.__init__(self)
        self.config = config
        # Used to pool TCP connections for upstream requests.
        self.session = requests.Session()

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

        :param request: the request to process.
        :type  request: twisted.web.server.Request
        """
        reactor.callInThread(self._handle_get, request)
        return NOT_DONE_YET

    def _handle_get(self, request):
        """
        Download the requested content using the content unit catalog and dispatch
        a celery task that causes Pulp to download the newly cached unit.

        :param request: The content request.
        :type  request: twisted.web.server.Request
        """
        catalog_path = urlparse(request.uri).path
        with Responder(request) as responder:
            try:
                catalog_entry = model.LazyCatalogEntry.objects(
                    path=catalog_path).order_by('importer_id').first()
                if not catalog_entry:
                    raise DoesNotExist()
                self._download(catalog_entry, request, responder)
            except DoesNotExist:
                logger.debug(_('Failed to find a catalog entry with path'
                               ' "{rel}".'.format(rel=catalog_path)))
                request.setResponseCode(NOT_FOUND)
            except PluginNotFound:
                msg = _('Catalog entry for {rel} references a plugin id'
                        ' which is not valid.')
                logger.error(msg.format(rel=catalog_path))
                request.setResponseCode(INTERNAL_SERVER_ERROR)
            except Exception:
                logger.exception(_('An unexpected error occurred while handling the request.'))
                request.setResponseCode(INTERNAL_SERVER_ERROR)

    def _download(self, catalog_entry, request, responder):
        """
        Build a nectar downloader and download the content from the catalog entry.
        The download is performed by the alternate content container, so it is possible
        to use the streamer in conjunction with alternate content sources.

        :param catalog_entry:   The catalog entry to download.
        :type  catalog_entry:   pulp.server.db.model.LazyCatalogEntry
        :param request:         The client content request.
        :type  request:         twisted.web.server.Request
        :param responder:       The file-like object that nectar should write to.
        :type  responder:       Responder
        """
        # Configure the primary downloader for alternate content sources
        plugin_importer, config, db_importer = repo_controller.get_importer_by_id(
            catalog_entry.importer_id)
        primary_downloader = plugin_importer.get_downloader_for_db_importer(
            db_importer, catalog_entry.url, working_dir='/tmp')
        pulp_request = request.getHeader(PULP_STREAM_REQUEST_HEADER)
        listener = StreamerListener(request, self.config, catalog_entry, pulp_request)
        primary_downloader.session = self.session
        primary_downloader.event_listener = listener

        # Build the alternate content source download request
        unit_model = plugins_api.get_unit_model_by_id(catalog_entry.unit_type_id)
        qs = unit_model.objects.filter(id=catalog_entry.unit_id).only(*unit_model.unit_key_fields)
        unit = qs.get()
        download_request = content_models.Request(
            catalog_entry.unit_type_id,
            unit.unit_key,
            catalog_entry.url,
            responder
        )

        alt_content_container = content_container.ContentContainer(threaded=False)
        alt_content_container.download(primary_downloader, [download_request], listener)
        primary_downloader.config.finalize()


class Responder(object):
    """
    This class provides an object that can be provided to Nectar instead of a
    file which forwards all write calls to the Twisted Request.
    """

    def __init__(self, request):
        """
        Initialize a new Responder.

        :param request: the request to forward the written data to.
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

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the Responder, which invokes the
        twisted.web.server.Request.finish method

        :param exc_type: The exception type, if any.
        :type  exc_type: type.TypeType
        :param exc_val: The exception instance, if any.
        :type  exc_val: Exception
        :param exc_tb: The traceback of the exception, if any.
        :type  exc_tb: traceback
        :return:
        """
        self.close()

    def close(self):
        """
        Forward the call to close the 'file' to the request.finish method.
        """
        reactor.callFromThread(self.finish_wrapper)

    def finish_wrapper(self):
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
