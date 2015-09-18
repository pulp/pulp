from httplib import INTERNAL_SERVER_ERROR, NOT_FOUND
from unittest import TestCase

from mock import Mock, patch
from mongoengine import DoesNotExist
from twisted.web.server import Request

from pulp.plugins.loader.exceptions import PluginNotFound
from pulp.server.lazy.streamer import Responder, StreamerListener, Streamer


MODULE_PREFIX = 'pulp.server.lazy.streamer.'


class TestStreamerListener(TestCase):

    @patch(MODULE_PREFIX + 'pulp_config', autospec=True)
    def test_download_headers(self, mock_config):
        mock_config.get.return_value = '1'
        mock_report = Mock()
        mock_report.headers = {'key': 'value', 'key2': 'value2'}
        expected_headers = mock_report.headers.copy()
        expected_headers['cache-control'] = 'public, s-maxage=1, max-age=1'
        listener = StreamerListener(Mock())

        listener.download_headers(mock_report)
        self.assertEqual(3, listener.request.setHeader.call_count)
        for expected, actual in zip(expected_headers.items(),
                                    listener.request.setHeader.call_args_list):
            self.assertEqual(expected, actual[0])

    def test_download_failed(self):
        mock_report = Mock()
        mock_report.error_report = {'response_code': '418', 'response_msg': 'I am a teapot.'}
        mock_report.url = 'https://example.com/teapot/'
        listener = StreamerListener(Mock())

        listener.download_failed(mock_report)
        self.assertEqual(('Connection', 'close'),
                         listener.request.setHeader.call_args_list[0][0])
        self.assertEqual(('Content-Length', '0'),
                         listener.request.setHeader.call_args_list[1][0])
        listener.request.setResponseCode.assert_called_once_with('418')


class TestStreamer(TestCase):

    def setUp(self):
        self.streamer = Streamer()
        self.request = Mock(spec=Request)

    @patch(MODULE_PREFIX + 'reactor', autospec=True)
    def test_render_GET(self, mock_reactor):
        self.streamer.render_GET(self.request)
        mock_reactor.callInThread.assert_called_once_with(self.streamer._download,
                                                          self.request)

    @patch(MODULE_PREFIX + 'nectar_request')
    @patch(MODULE_PREFIX + 'content_controller')
    @patch(MODULE_PREFIX + 'repo_controller')
    @patch(MODULE_PREFIX + 'model')
    @patch(MODULE_PREFIX + 'Responder.__exit__')
    @patch(MODULE_PREFIX + 'Responder.__enter__')
    def test_download(self, mock_enter, mock_exit, mock_model, mock_repo_controller,
                      mock_content_controller, nectar_request):
        # Setup
        self.request.uri = '/a/resource?k=v'
        mock_importer, mock_config = Mock(), Mock()
        mock_downloader = mock_importer.get_downloader.return_value
        mock_download_request = nectar_request.DownloadRequest.return_value
        mock_catalog = mock_model.LazyCatalogEntry.objects.return_value.\
            order_by('-plugin_id').first.return_value
        mock_catalog.data = {'k': 'v'}
        mock_repo_controller.get_importer_by_id.return_value = (mock_importer, mock_config)

        # Test
        self.streamer._download(self.request)
        mock_exit.assert_called_once_with(None, None, None)

        # Validate the unit importer retrieval
        mock_model.LazyCatalogEntry.objects.assert_called_once_with(relative_path='a/resource')
        query_set = mock_model.LazyCatalogEntry.objects.return_value
        self.assertEqual(1, query_set.order_by('-plugin_id').first.call_count)
        mock_repo_controller.get_importer_by_id.assert_called_once_with(mock_catalog.plugin_id)

        # Validate building and invoking the downloader
        mock_importer.get_downloader.assert_called_once_with(mock_config, mock_catalog.url, k='v')
        nectar_request.DownloadRequest.assert_called_once_with(mock_catalog.url,
                                                               mock_enter.return_value)
        mock_downloader.download_one.assert_called_once_with(mock_download_request, events=True)

        # Validate that the download task is dispatched
        mock_content_controller.queue_download.assert_called_once_with(mock_catalog.plugin_id,
                                                                       mock_catalog.unit_locator,
                                                                       mock_catalog.url,
                                                                       mock_catalog.data)

    @patch(MODULE_PREFIX + 'repo_controller', autospec=True)
    @patch(MODULE_PREFIX + 'model', Mock())
    def test_download_no_plugin(self, mock_repo_controller):
        self.request.uri = '/a/resource?k=v'
        mock_repo_controller.get_importer_by_id.side_effect = PluginNotFound()

        self.streamer._download(self.request)
        self.request.setResponseCode.assert_called_once_with(INTERNAL_SERVER_ERROR)

    @patch(MODULE_PREFIX + 'logger')
    @patch(MODULE_PREFIX + 'model')
    def test_download_no_catalog(self, mock_model, mock_logger):
        self.request.uri = '/a/resource?k=v'
        mock_model.LazyCatalogEntry.objects.return_value.\
            order_by('-plugin_id').first.side_effect = DoesNotExist

        self.streamer._download(self.request)
        mock_logger.debug.assert_called_once_with('Failed to find a catalog entry '
                                                  'with relative path "a/resource".')
        self.request.setResponseCode.assert_called_once_with(NOT_FOUND)

    @patch(MODULE_PREFIX + 'logger')
    @patch(MODULE_PREFIX + 'model')
    def test_download_unexpected_failure(self, mock_model, mock_logger):
        self.request.uri = '/a/resource?k=v'
        mock_model.LazyCatalogEntry.objects.return_value. \
            order_by('-plugin_id').first = OSError('Disaster.')

        self.streamer._download(self.request)
        mock_logger.exception.assert_called_once_with('An unexpected error occurred while '
                                                      'handling the request.')
        self.request.setResponseCode.assert_called_once_with(INTERNAL_SERVER_ERROR)


class TestResponder(TestCase):

    def test_enter(self):
        responder = Responder(Mock())
        result = responder.__enter__()
        self.assertIs(responder, result)

    def test_exit(self):
        responder = Responder(Mock())
        responder.close = Mock()

        responder.__exit__(None, None, None)
        responder.close.assert_called_once_with()

    @patch('pulp.server.lazy.streamer.reactor')
    def test_close(self, mock_reactor):
        responder = Responder(Mock())
        responder.close()
        mock_reactor.callFromThread.assert_called_once_with(responder.request.finish)

    @patch('pulp.server.lazy.streamer.reactor')
    def test_write(self, mock_reactor):
        responder = Responder(Mock())
        responder.write('some data')
        mock_reactor.callFromThread.assert_called_once_with(responder.request.write,
                                                            'some data')

    @patch('pulp.server.lazy.streamer.reactor')
    def test_with(self, mock_reactor):
        mock_request = Mock()
        with Responder(mock_request) as r:
            r.write('some data')

        mock_calls = mock_reactor.callFromThread.call_args_list
        self.assertEqual((mock_request.write, 'some data'), mock_calls[0][0])
        self.assertEqual((mock_request.finish,), mock_calls[1][0])
