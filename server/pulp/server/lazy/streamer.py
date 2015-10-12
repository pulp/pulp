from gettext import gettext as _
from httplib import NOT_FOUND, INTERNAL_SERVER_ERROR
from urlparse import urlparse
import logging

from mongoengine import DoesNotExist
from nectar import listener as nectar_listener
from nectar import request as nectar_request
from twisted.internet import reactor
from twisted.web import resource
from twisted.web.server import NOT_DONE_YET

from pulp.server.config import config as pulp_config
from pulp.server.constants import PULP_STREAM_REQUEST_HEADER
from pulp.server.db import model
from pulp.server.controllers import repository as repo_controller
from pulp.server.controllers import content as content_controller
from pulp.plugins.loader.exceptions import PluginNotFound

logger = logging.getLogger(__name__)


class StreamerListener(nectar_listener.DownloadEventListener):
    """
    This DownloadEventListener subclass's purpose is to set the
    response headers on the given HTTP request. This includes setting
    the cache-control header with the max-age which is loaded from the
    Pulp server.conf.
    """

    def __init__(self, request):
        """
        Initialize a StreamerNectarListener.

        :param request: the request to set the response headers for.
        :type  request: twisted.web.server.Request
        """
        super(StreamerListener, self).__init__()
        self.request = request

    def download_headers(self, report):
        """
        Modify incoming headers to include the cache timeout value from the Pulp
        server configuration. This is used by Squid to determine what content
        can be removed from its cache when its reaper runs.

        :param report: The download report for this request.
        :type  report: nectar.report.DownloadReport
        """
        for header_key, header_value in report.headers.items():
            self.request.setHeader(header_key, header_value)

        max_age = {'max_age': pulp_config.get('streamer', 'cache_timeout')}
        cache_header = 'public, s-maxage=%(max_age)s, max-age=%(max_age)s' % max_age
        self.request.setHeader('cache-control', cache_header)

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
        error_report = report.error_report.copy()
        error_report['url'] = report.url
        logger.info(_('Download of %(url)s failed: HTTP %(response_code)s '
                      '%(response_msg)s' % error_report))

        # Currently Nectar returns headers with a content-length even
        # when it doesn't download anything.
        self.request.setHeader('Connection', 'close')
        self.request.setHeader('Content-Length', '0')
        if 'response_code' in report.error_report:
            self.request.setResponseCode(report.error_report['response_code'])


class Streamer(resource.Resource):
    """
    Define the web resource that streams content from the upstream repository
    to the client.
    """
    # Ensure self.getChild isn't called as this has no child resources
    isLeaf = True

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

    @staticmethod
    def _handle_get(request):
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
                Streamer._download(catalog_entry, request, responder)

                # Only dispatch the task if the request didn't originate from Pulp.
                if not request.getHeader(PULP_STREAM_REQUEST_HEADER):
                    content_controller.queue_download_one(catalog_entry)
            except DoesNotExist:
                logger.debug(_('Failed to find a catalog entry with path'
                               ' "{rel}".'.format(rel=catalog_path)))
                request.setResponseCode(NOT_FOUND)
            except PluginNotFound:
                msg = _('Catalog entry for {rel} references a plugin id'
                        ' which is not a valid.')
                logger.error(msg.format(rel=catalog_path))
                request.setResponseCode(INTERNAL_SERVER_ERROR)
            except Exception:
                logger.exception(_('An unexpected error occurred while handling the request.'))
                request.setResponseCode(INTERNAL_SERVER_ERROR)

    @staticmethod
    def _download(catalog_entry, request, responder):
        """
        Build a nectar downloader and download the content from the catalog entry.

        :param catalog_entry:   The catalog entry to download.
        :type  catalog_entry:   pulp.server.db.model.LazyCatalogEntry
        :param request:         The client content request.
        :type  request:         twisted.web.server.Request
        :param responder:       The file-like object that nectar should write to.
        :type  responder:       Responder
        """

        importer, config = repo_controller.get_importer_by_id(catalog_entry.importer_id)

        download_request = nectar_request.DownloadRequest(catalog_entry.url, responder)
        downloader = importer.get_downloader(config, catalog_entry.url,
                                             **catalog_entry.data)
        downloader.event_listener = StreamerListener(request)
        downloader.download_one(download_request, events=True)


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
        reactor.callFromThread(self.request.finish)

    def write(self, data):
        """
        Forward the data to the request.write method, which writes data to
        the transport (if not responding to a HEAD request).

        :param data: A string to write to the response.
        :type  data: str
        """
        reactor.callFromThread(self.request.write, data)
