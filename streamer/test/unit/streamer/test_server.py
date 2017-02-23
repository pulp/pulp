from httplib import NOT_FOUND, INTERNAL_SERVER_ERROR

from mock import Mock, patch, call
from mongoengine import DoesNotExist, NotUniqueError
from nectar.report import DownloadReport

from pulp.common.compat import unittest
from pulp.devel.unit.util import SideEffect
from pulp.plugins.loader.exceptions import PluginNotFound
from pulp.server import constants
from pulp.streamer.server import (
    Responder, Streamer, DownloadListener, DownloadFailed, HOP_BY_HOP_HEADERS
)


MODULE_PREFIX = 'pulp.streamer.server.'


class TestListener(unittest.TestCase):

    def test_download_headers(self):
        request = Mock(
            uri='http://content-world.com/content/bear.rpm',
            headers={})
        request.setHeader.side_effect = request.headers.__setitem__
        report = DownloadReport('', '')
        report.headers = {
            'A': 1,
            'B': 2,
        }

        # should be ignored.
        report.headers.update({k: '' for k in HOP_BY_HOP_HEADERS})

        config = Mock(properties={
            'streamer': {
                'cache_timeout': 100
            }
        })

        def get(s, p):
            return config.properties[s][p]

        config.get.side_effect = get
        streamer = Mock(config=config)

        # test
        listener = DownloadListener(streamer, request)
        listener.download_headers(report)

        # validation
        self.assertEqual(
            request.headers,
            {
                'Cache-Control': 'public, s-maxage=100, max-age=100',
                'A': 1,
                'B': 2,
            })

    def test_download_failed(self):
        report = DownloadReport('', '')
        report.error_report['response_code'] = 1234

        # test
        listener = DownloadListener(None, None)
        listener.download_failed(report)

    def test_download_failed_not_code(self):
        report = DownloadReport('', '')

        # test
        listener = DownloadListener(None, None)
        listener.download_failed(report)


class TestStreamer(unittest.TestCase):

    @patch(MODULE_PREFIX + 'reactor')
    def test_render_GET(self, reactor):
        request = Mock()

        # test
        streamer = Streamer(Mock())
        streamer.render_GET(request)

        # validation
        reactor.callInThread.assert_called_once_with(streamer._handle_get, request)

    @patch(MODULE_PREFIX + 'Responder')
    @patch(MODULE_PREFIX + 'Streamer._on_succeeded')
    @patch(MODULE_PREFIX + 'Streamer._download')
    @patch(MODULE_PREFIX + 'LazyCatalogEntry')
    @patch(MODULE_PREFIX + 'reactor', Mock())
    def test_handle_get(self, model, _download, _on_succeeded, responder):
        """
         Three catalog entries.
         The 1st download fails but succeeds on the 2nd.
         The 3rd is not tried.
        """
        request = Mock(uri='http://content-world.com/content/bear.rpm')
        responder.return_value.__enter__.return_value = responder.return_value
        report = DownloadReport('', '')
        _download.side_effect = SideEffect(
            DownloadFailed(report),
            report,
            None)
        catalog = [
            Mock(url='url-a'),
            Mock(url='url-b'),
            Mock(url='url-c'),  # not tried.
        ]
        model.objects.filter.return_value.order_by.return_value.all.return_value = catalog
        model.objects.filter.return_value.order_by.return_value.count.return_value = len(catalog)

        # test
        streamer = Streamer(Mock())
        streamer._handle_get(request)

        # validation
        model.objects.filter.assert_called_once_with(path='/content/bear.rpm')
        model.objects.filter.return_value.order_by.\
            assert_called_once_with('-_id', '-revision')
        responder.assert_called_once_with(request)
        _on_succeeded.assert_called_once_with(catalog[1], request, report)
        self.assertEqual(
            _download.call_args_list,
            [
                call(request, catalog[0], responder.return_value),
                call(request, catalog[1], responder.return_value)
            ])

    @patch(MODULE_PREFIX + 'Responder')
    @patch(MODULE_PREFIX + 'Streamer._on_all_failed')
    @patch(MODULE_PREFIX + 'Streamer._download')
    @patch(MODULE_PREFIX + 'LazyCatalogEntry')
    @patch(MODULE_PREFIX + 'reactor', Mock())
    def test_handle_get_all_failed(self, model, _download, _on_all_failed, responder):
        """
         Three catalog entries.
         All (3) failed.
        """
        request = Mock(uri='http://content-world.com/content/bear.rpm')
        responder.return_value.__enter__.return_value = responder.return_value
        report = DownloadReport('', '')
        _download.side_effect = SideEffect(
            PluginNotFound(),
            DoesNotExist(),
            DownloadFailed(report))
        catalog = [
            Mock(url='url-a'),
            Mock(url='url-b'),
            Mock(url='url-c'),
        ]
        model.objects.filter.return_value.order_by.return_value.all.return_value = catalog
        model.objects.filter.return_value.order_by.return_value.count.return_value = len(catalog)

        # test
        streamer = Streamer(Mock())
        streamer._handle_get(request)

        # validation
        model.objects.filter.assert_called_once_with(path='/content/bear.rpm')
        model.objects.filter.return_value.order_by.\
            assert_called_once_with('-_id', '-revision')
        responder.assert_called_once_with(request)
        _on_all_failed.assert_called_once_with(request)
        self.assertEqual(
            _download.call_args_list,
            [
                call(request, catalog[0], responder.return_value),
                call(request, catalog[1], responder.return_value),
                call(request, catalog[2], responder.return_value)
            ])

    @patch(MODULE_PREFIX + 'Responder')
    @patch(MODULE_PREFIX + 'Streamer._download')
    @patch(MODULE_PREFIX + 'LazyCatalogEntry')
    @patch(MODULE_PREFIX + 'reactor', Mock())
    def test_handle_get_no_catalog_matched(self, model, _download, responder):
        """
        No catalog entries matched.
        """
        responder.return_value.__enter__.return_value = responder.return_value
        request = Mock(uri='http://content-world.com/content/bear.rpm')
        catalog = []
        model.objects.filter.return_value.order_by.return_value.all.return_value = catalog
        model.objects.filter.return_value.order_by.return_value.count.return_value = len(catalog)

        # test
        streamer = Streamer(Mock())
        streamer._handle_get(request)

        # validation
        model.objects.filter.assert_called_once_with(path='/content/bear.rpm')
        model.objects.filter.return_value.order_by.\
            assert_called_once_with('-_id', '-revision')
        request.setResponseCode.assert_called_once_with(NOT_FOUND)
        self.assertFalse(_download.called)

    @patch(MODULE_PREFIX + 'LazyCatalogEntry')
    @patch(MODULE_PREFIX + 'reactor', Mock())
    def test_handle_get_failed_badly(self, model):
        request = Mock()
        model.objects.filter.side_effect = ValueError()

        # test
        streamer = Streamer(Mock())
        streamer._handle_get(request)

        # validation
        request.setResponseCode.assert_called_once_with(INTERNAL_SERVER_ERROR)

    @patch(MODULE_PREFIX + 'Streamer._insert_deferred')
    def test_on_succeeded_client_requested(self, _insert_deferred):
        entry = Mock(url='url-a')
        request = Mock(uri='http://content-world.com/content/bear.rpm')
        request.getHeader.side_effect = {
            constants.PULP_STREAM_REQUEST_HEADER: False
        }.__getitem__
        report = DownloadReport('', '')
        report.headers = {
            'A': 1,
            'B': 2,
        }

        # test
        streamer = Streamer(Mock())
        streamer._on_succeeded(entry, request, report)

        # validation
        _insert_deferred.assert_called_once_with(entry)

    @patch(MODULE_PREFIX + 'Streamer._insert_deferred')
    def test_on_succeeded_pulp_requested(self, _insert_deferred):
        entry = Mock(url='url-a')
        request = Mock(uri='http://content-world.com/content/bear.rpm')
        request.getHeader.side_effect = {
            constants.PULP_STREAM_REQUEST_HEADER: True
        }.__getitem__
        report = DownloadReport('', '')
        report.headers = {
            'A': 1,
            'B': 2,
        }

        # test
        streamer = Streamer(Mock())
        streamer._on_succeeded(entry, request, report)

        # validation
        self.assertFalse(_insert_deferred.called)

    def test_on_all_failed(self):
        request = Mock(uri='http://content-world.com/content/bear.rpm')
        request.getHeader.side_effect = {
            constants.PULP_STREAM_REQUEST_HEADER: True
        }.__getitem__

        # test
        streamer = Streamer(Mock())
        streamer._on_all_failed(request)

        # validation
        request.setHeader.assert_called_once_with('Content-Length', '0')
        request.setResponseCode.assert_called_once_with(NOT_FOUND)

    @patch(MODULE_PREFIX + 'ContainerRequest')
    @patch(MODULE_PREFIX + 'ContentContainer')
    @patch(MODULE_PREFIX + 'Streamer._get_downloader')
    @patch(MODULE_PREFIX + 'Streamer._get_unit')
    def test_download(self, _get_unit, _get_downloader, container, request):
        twisted_request = Mock()
        unit = Mock(unit_id=12, unit_type_id='test')
        listener = Mock(
            succeeded_reports=[
                Mock()
            ],
            failed_reports=[])
        downloader = Mock(event_listener=listener)
        responder = Mock()
        entry = Mock(url='url-a')
        _get_unit.return_value = unit
        _get_downloader.return_value = downloader

        # test
        streamer = Streamer(Mock())
        report = streamer._download(twisted_request, entry, responder)

        # validation
        _get_unit.assert_called_once_with(entry)
        _get_downloader.assert_called_once_with(twisted_request, entry)
        request.assert_called_once_with(
            entry.unit_type_id,
            unit.unit_key,
            entry.url,
            responder)
        container.assert_called_once_with(threaded=False)
        container.return_value.download(downloader, [request.return_value], listener)
        downloader.config.finalize.assert_called_once_with()
        self.assertEqual(report, listener.succeeded_reports[0])

    @patch(MODULE_PREFIX + 'ContainerRequest')
    @patch(MODULE_PREFIX + 'ContentContainer')
    @patch(MODULE_PREFIX + 'Streamer._get_downloader')
    @patch(MODULE_PREFIX + 'Streamer._get_unit')
    def test_download_404(self, _get_unit, _get_downloader, container, request):
        twisted_request = Mock()
        unit = Mock(unit_id=12, unit_type_id='test')
        listener = Mock(
            succeeded_reports=[],
            failed_reports=[
                Mock()
            ])
        downloader = Mock(event_listener=listener)
        downloader.config.finalize.side_effect = ValueError()
        responder = Mock()
        entry = Mock(url='url-a')
        _get_unit.return_value = unit
        _get_downloader.return_value = downloader

        # test
        streamer = Streamer(Mock())
        self.assertRaises(DownloadFailed, streamer._download, twisted_request, entry, responder)

        # validation
        _get_unit.assert_called_once_with(entry)
        _get_downloader.assert_called_once_with(twisted_request, entry)
        request.assert_called_once_with(
            entry.unit_type_id,
            unit.unit_key,
            entry.url,
            responder)
        container.assert_called_once_with(threaded=False)
        container.return_value.download(downloader, [request.return_value], listener)
        downloader.config.finalize.assert_called_once_with()

    @patch(MODULE_PREFIX + 'DownloadListener')
    @patch(MODULE_PREFIX + 'repo_controller')
    def test_get_downloader(self, controller, listener):
        request = Mock()
        entry = Mock(importer_id='123')
        importer = Mock()
        config = Mock()
        model = Mock()
        plugin = (importer, config, model)
        controller.get_importer_by_id.return_value = plugin

        # test
        streamer = Streamer(Mock())
        streamer.session = Mock()
        downloader = streamer._get_downloader(request, entry)

        # validation
        controller.get_importer_by_id.assert_called_once_with(entry.importer_id)
        config.flatten.assert_called_once_with()
        importer.get_downloader_for_db_importer.assert_called_once_with(
            model, entry.url, working_dir='/tmp')
        listener.assert_called_once_with(streamer, request)
        self.assertEqual(downloader, importer.get_downloader_for_db_importer.return_value)
        self.assertEqual(downloader.event_listener, listener.return_value)
        self.assertEqual(downloader.session, streamer.session)

    @patch(MODULE_PREFIX + 'AggregatingEventListener')
    @patch(MODULE_PREFIX + 'repo_controller')
    def test_get_downloader_not_found(self, controller, listener):
        entry = Mock(importer_id='123')
        controller.get_importer_by_id.side_effect = PluginNotFound()

        # test
        streamer = Streamer(Mock())
        self.assertRaises(PluginNotFound, streamer._get_downloader, Mock(), entry)

    @patch(MODULE_PREFIX + 'plugin_api')
    def test_get_unit(self, plugin_api):
        q_set = Mock()
        q_set.filter.return_value = q_set
        q_set.only.return_value = q_set
        model = Mock(
            objects=q_set,
            unit_key_fields=[1, 2])
        entry = Mock(importer_id='123', unit_id=345, unit_type_id='xx')
        plugin_api.get_unit_model_by_id.return_value = model

        # test
        streamer = Streamer(Mock())
        unit = streamer._get_unit(entry)

        # validation
        plugin_api.get_unit_model_by_id.assert_called_once_with(entry.unit_type_id)
        q_set.filter.assert_called_once_with(id=entry.unit_id)
        q_set.only.assert_called_once_with(*model.unit_key_fields)
        self.assertEqual(unit, q_set.get.return_value)

    @patch(MODULE_PREFIX + 'plugin_api')
    def test_get_unit_not_found(self, plugin_api):
        q_set = Mock()
        q_set.filter.return_value = q_set
        q_set.only.return_value = q_set
        model = Mock(
            objects=q_set,
            unit_key_fields=[1, 2])
        entry = Mock(importer_id='123', unit_id=345, unit_type_id='xx')
        plugin_api.get_unit_model_by_id.return_value = model
        q_set.get.side_effect = DoesNotExist

        # test
        streamer = Streamer(Mock())
        self.assertRaises(DoesNotExist, streamer._get_unit, entry)

    @patch(MODULE_PREFIX + 'DeferredDownload')
    def test_insert_deferred(self, model):
        entry = Mock(unit_id=123, unit_type_id='xx')
        model.return_value.save.side_effect = NotUniqueError()

        # test
        streamer = Streamer(Mock())
        streamer._insert_deferred(entry)

        # validation
        model.assert_called_once_with(unit_id=entry.unit_id, unit_type_id=entry.unit_type_id)
        model.return_value.save.assert_called_once_with()


class TestResponder(unittest.TestCase):

    def test_enter(self):
        """
        `__enter__` returns the instance of the class.
        """
        responder = Responder(Mock())
        result = responder.__enter__()
        self.assertTrue(responder is result)

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
        mock_reactor.callFromThread.assert_called_once_with(responder.finish)

    def test_finish(self):
        """Assert the ``finish`` method is called by its wrapper"""
        responder = Responder(Mock())
        responder.finish()
        responder.request.finish.assert_called_once_with()

    @patch(MODULE_PREFIX + 'logger')
    def test_finish_exception(self, mock_logger):
        """Assert that if ``finish`` raises a RuntimeError, it's logged."""
        responder = Responder(Mock())
        responder.request.finish.side_effect = RuntimeError('Womp womp')
        responder.finish()
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
        self.assertEqual((r.finish,), mock_calls[1][0])
