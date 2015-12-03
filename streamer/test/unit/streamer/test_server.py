from httplib import INTERNAL_SERVER_ERROR, NOT_FOUND
from unittest import TestCase

from mock import Mock, patch
from mongoengine import NotUniqueError
from twisted.web.server import Request

from pulp.plugins.loader.exceptions import PluginNotFound
from pulp.server.constants import PULP_STREAM_REQUEST_HEADER
from pulp.streamer import Responder, StreamerListener, Streamer


MODULE_PREFIX = 'pulp.streamer.server.'


class TestStreamerListener(TestCase):

    def test_download_headers(self):
        """
        The cache-control headers are set appropriately.
        """
        mock_config = Mock()
        mock_config.get.return_value = '1'
        mock_report = Mock()
        mock_report.headers = {'key': 'value', 'key2': 'value2'}
        expected_headers = mock_report.headers.copy()
        expected_headers['cache-control'] = 'public, s-maxage=1, max-age=1'
        listener = StreamerListener(Mock(), mock_config)

        listener.download_headers(mock_report)
        self.assertEqual(3, listener.request.setHeader.call_count)
        for expected, actual in zip(expected_headers.items(),
                                    listener.request.setHeader.call_args_list):
            self.assertEqual(expected, actual[0])

    def test_download_failed(self):
        """
        The content-length is corrected since Nectar does not download anything if
        it receives a non-200 response.
        """
        mock_report = Mock()
        mock_report.error_report = {'response_code': '418', 'response_msg': 'I am a teapot.'}
        mock_report.url = 'https://example.com/teapot/'
        listener = StreamerListener(Mock(), Mock())

        listener.download_failed(mock_report)
        self.assertEqual(('Connection', 'close'),
                         listener.request.setHeader.call_args_list[0][0])
        self.assertEqual(('Content-Length', '0'),
                         listener.request.setHeader.call_args_list[1][0])
        listener.request.setResponseCode.assert_called_once_with('418')


class TestStreamer(TestCase):

    def setUp(self):
        self.config = Mock()
        self.streamer = Streamer(self.config)
        self.request = Mock(spec=Request)

    @patch(MODULE_PREFIX + 'reactor', autospec=True)
    def test_render_GET(self, mock_reactor):
        """
        The handler for GET requests is invoked in a thread so that nectar is safe
        to use.
        """
        self.streamer.render_GET(self.request)
        mock_reactor.callInThread.assert_called_once_with(self.streamer._handle_get,
                                                          self.request)

    @patch(MODULE_PREFIX + 'model')
    @patch(MODULE_PREFIX + 'Responder.__exit__')
    @patch(MODULE_PREFIX + 'Responder.__enter__')
    @patch(MODULE_PREFIX + 'Streamer._download')
    def test_handle_get(self, mock_download, mock_enter, mock_exit, mock_model):
        """
        When the streamer receives a request, the content is downloaded and a task
        is dispatched.
        """
        # Setup
        self.streamer._add_deferred_download_entry = Mock()
        self.request.uri = '/a/resource?k=v'
        self.request.getHeader.return_value = None
        mock_catalog = mock_model.LazyCatalogEntry.objects.return_value.order_by(
            '-plugin_id').first.return_value

        # Test
        self.streamer._handle_get(self.request)
        mock_exit.assert_called_once_with(None, None, None)
        mock_model.LazyCatalogEntry.objects.assert_called_once_with(path='/a/resource')
        query_set = mock_model.LazyCatalogEntry.objects.return_value
        self.assertEqual(1, query_set.order_by('importer_id').first.call_count)
        mock_download.assert_called_once_with(mock_catalog, self.request,
                                              mock_enter.return_value)
        self.streamer._add_deferred_download_entry.assert_called_once_with(self.request,
                                                                           mock_catalog)

    @patch(MODULE_PREFIX + 'repo_controller', autospec=True)
    @patch(MODULE_PREFIX + 'model', Mock())
    def test_handle_get_no_plugin(self, mock_repo_controller):
        """
        When the _download helper method fails to find the plugin, it raises an exception.
        """
        self.request.uri = '/a/resource?k=v'
        mock_repo_controller.get_importer_by_id.side_effect = PluginNotFound()

        self.streamer._handle_get(self.request)
        self.request.setResponseCode.assert_called_once_with(INTERNAL_SERVER_ERROR)

    @patch(MODULE_PREFIX + 'logger')
    @patch(MODULE_PREFIX + 'model')
    def test_handle_get_no_catalog(self, mock_model, mock_logger):
        """
        When there is no catalog entry a DoesNotExist exception is raised and handled.
        """
        self.request.uri = '/a/resource?k=v'
        mock_model.LazyCatalogEntry.objects.return_value.\
            order_by('importer_id').first.return_value = None

        self.streamer._handle_get(self.request)
        mock_logger.debug.assert_called_once_with('Failed to find a catalog entry '
                                                  'with path "/a/resource".')
        self.request.setResponseCode.assert_called_once_with(NOT_FOUND)

    @patch(MODULE_PREFIX + 'logger')
    @patch(MODULE_PREFIX + 'model')
    def test_handle_get_unexpected_failure(self, mock_model, mock_logger):
        """
        When an unexpected exception occurs, the exception is logged. Further, an
        HTTP 500 is returned.
        """
        self.request.uri = '/a/resource?k=v'
        mock_model.LazyCatalogEntry.objects.return_value. \
            order_by('importer_id').first = OSError('Disaster.')

        self.streamer._handle_get(self.request)
        mock_logger.exception.assert_called_once_with('An unexpected error occurred while '
                                                      'handling the request.')
        self.request.setResponseCode.assert_called_once_with(INTERNAL_SERVER_ERROR)

    @patch(MODULE_PREFIX + 'StreamerListener')
    @patch(MODULE_PREFIX + 'ContentContainer')
    @patch(MODULE_PREFIX + 'nectar_request.DownloadRequest')
    @patch(MODULE_PREFIX + 'repo_controller', autospec=True)
    def test_download(self, mock_repo_controller, mock_dl_request, mock_container, mock_listener):
        # Setup
        mock_catalog = Mock()
        mock_catalog.importer_id = 'mock_id'
        mock_catalog.url = 'http://dev.null/'
        mock_catalog.data = {'k': 'v'}
        mock_request = Mock()
        mock_responder = Mock()
        mock_importer = Mock()
        mock_importer_config = Mock()
        mock_downloader = mock_importer.get_downloader.return_value
        mock_repo_controller.get_importer_by_id.return_value = (mock_importer,
                                                                mock_importer_config)

        # Test
        self.streamer._download(mock_catalog, mock_request, mock_responder)
        mock_repo_controller.get_importer_by_id.assert_called_once_with(mock_catalog.importer_id)
        mock_dl_request.assert_called_once_with(mock_catalog.url, mock_responder)
        mock_importer.get_downloader.assert_called_once_with(
            mock_importer_config, mock_catalog.url, **mock_catalog.data)
        mock_container.assert_called_once_with(threaded=False)
        mock_container.return_value.download.assert_called_once_with(
            mock_downloader,
            [mock_dl_request.return_value],
            mock_listener.return_value
        )
        mock_downloader.config.finalize.assert_called_once_with()

    @patch(MODULE_PREFIX + 'model.DeferredDownload', autospec=True)
    def test_add_deferred_download_entry(self, mock_deferred_download):
        # Setup
        mock_request = Mock()
        mock_request.getHeader.return_value = None
        mock_catalog_entry = Mock()
        mock_catalog_entry.unit_id = 'abc'
        mock_catalog_entry.unit_type_id = '123'

        # Test
        self.streamer._add_deferred_download_entry(mock_request, mock_catalog_entry)
        mock_request.getHeader.assert_called_once_with(PULP_STREAM_REQUEST_HEADER)
        mock_deferred_download.assert_called_once_with(unit_id='abc', unit_type_id='123')
        mock_deferred_download.return_value.save.assert_called_once_with()

    @patch(MODULE_PREFIX + 'model.DeferredDownload', autospec=True)
    def test_add_deferred_download_entry_not_unique(self, mock_deferred_download):
        # Setup
        mock_request = Mock()
        mock_request.getHeader.return_value = None
        mock_catalog_entry = Mock()
        mock_deferred_download.return_value.save.side_effect = NotUniqueError()

        # Test
        self.streamer._add_deferred_download_entry(mock_request, mock_catalog_entry)
        mock_deferred_download.return_value.save.assert_called_once_with()

    @patch(MODULE_PREFIX + 'model.DeferredDownload', autospec=True)
    def test_add_deferred_download_entry_pulp_request(self, mock_deferred_download):
        # Setup
        mock_request = Mock()
        mock_request.getHeader.return_value = 'something'
        mock_catalog_entry = Mock()

        # Test
        self.streamer._add_deferred_download_entry(mock_request, mock_catalog_entry)
        self.assertEqual(0, mock_deferred_download.return_value.save.call_count)


class TestResponder(TestCase):

    def test_enter(self):
        """
        `__enter__` returns the instance of the class.
        """
        responder = Responder(Mock())
        result = responder.__enter__()
        self.assertIs(responder, result)

    def test_exit(self):
        """
        `__exit__` invokes the `close` method on the instance.
        """
        responder = Responder(Mock())
        responder.close = Mock()

        responder.__exit__(None, None, None)
        responder.close.assert_called_once_with()

    @patch(MODULE_PREFIX + 'reactor')
    def test_close(self, mock_reactor):
        """
        `close` invokes the request.finish method on the Twisted request.
        """
        responder = Responder(Mock())
        responder.close()
        mock_reactor.callFromThread.assert_called_once_with(responder.finish_wrapper)

    def test_finish_wrapper(self):
        """Assert the ``finish`` method is called by its wrapper"""
        responder = Responder(Mock())
        responder.finish_wrapper()
        responder.request.finish.assert_called_once_with()

    @patch(MODULE_PREFIX + 'logger')
    def test_finish_wrapper_exception(self, mock_logger):
        """Assert that if ``finish`` raises a RuntimeError, it's logged."""
        responder = Responder(Mock())
        responder.request.finish.side_effect = RuntimeError('Womp womp')
        responder.finish_wrapper()
        responder.request.finish.assert_called_once_with()
        mock_logger.debug.assert_called_once_with('Womp womp')

    @patch(MODULE_PREFIX + 'reactor')
    def test_write(self, mock_reactor):
        """
        `write` forwards all data to the `request.write` method.
        """
        responder = Responder(Mock())
        responder.write('some data')
        mock_reactor.callFromThread.assert_called_once_with(responder.request.write,
                                                            'some data')

    @patch(MODULE_PREFIX + 'reactor')
    def test_with(self, mock_reactor):
        """
        The Responder class supports context managers.
        """
        mock_request = Mock()
        with Responder(mock_request) as r:
            r.write('some data')

        mock_calls = mock_reactor.callFromThread.call_args_list
        self.assertEqual((mock_request.write, 'some data'), mock_calls[0][0])
        self.assertEqual((r.finish_wrapper,), mock_calls[1][0])
