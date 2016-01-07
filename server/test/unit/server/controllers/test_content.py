from mock import patch, Mock, call
from unittest import TestCase

from mongoengine import DoesNotExist

from pulp.plugins.conduits.mixins import LazyStatusConduitException
from pulp.server.exceptions import PulpCodedTaskFailedException, PulpCodedTaskException
from pulp.server.controllers import content as content_controller

MODULE_PATH = 'pulp.server.controllers.content.'


class TestContentSourcesRefreshStep(TestCase):

    @patch('pulp.server.controllers.content.ContentSourcesRefreshStep.process_main')
    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_process_main_one(self, mock_load, mock_process_main):
        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1})),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2})),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3})),
        }

        mock_load.return_value = sources
        conduit = content_controller.ContentSourcesConduit('task_id')
        step = content_controller.ContentSourcesRefreshStep(conduit, content_source_id='C')
        step.process()
        step.process_main.assert_called_with(item=sources['C'])
        self.assertEquals(step.progress_successes, 1)

    @patch('pulp.server.controllers.content.ContentSourcesRefreshStep.process_main')
    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_process_main_all(self, mock_load, mock_process_main):
        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1})),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2})),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3})),
        }

        mock_load.return_value = sources
        conduit = content_controller.ContentSourcesConduit('task_id')
        step = content_controller.ContentSourcesRefreshStep(conduit)
        step.process()
        expected_call_list = []
        for item in step.get_iterator():
            expected_call_list.append(call(item=item))
        self.assertEqual(expected_call_list, step.process_main.call_args_list)
        self.assertEquals(step.progress_successes, 3)

    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_process_with_failure(self, mock_load):
        successful_report = Mock()
        successful_report.dict.return_value = {}
        successful_report.succeeded = True

        unsuccessful_report = Mock()
        unsuccessful_report.dict.return_value = {}
        unsuccessful_report.succeeded = False

        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1}), descriptor={'name': 'A'},
                      refresh=Mock(return_value=[successful_report])),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2}), descriptor={'name': 'B'},
                      refresh=Mock(return_value=[unsuccessful_report])),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3}), descriptor={'name': 'C'},
                      refresh=Mock(return_value=[successful_report])),
        }

        mock_load.return_value = sources
        conduit = content_controller.ContentSourcesConduit('task_id')
        step = content_controller.ContentSourcesRefreshStep(conduit)
        self.assertRaises(PulpCodedTaskFailedException, step.process)
        self.assertEquals(step.progress_successes, 2)
        self.assertEqual(step.progress_failures, 1)

    @patch('pulp.server.controllers.content.ContentSourcesRefreshStep.process_main',
           side_effect=Exception('boom'))
    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_process_with_unexpected_exception(self, mock_load, mock_process_main):
        successful_report = Mock()
        successful_report.dict.return_value = {}
        successful_report.succeeded = True

        unsuccessful_report = Mock()
        unsuccessful_report.dict.return_value = {}
        unsuccessful_report.succeeded = False

        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1}), descriptor={'name': 'A'},
                      refresh=Mock(return_value=[successful_report])),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2}), descriptor={'name': 'B'},
                      refresh=Mock(return_value=[unsuccessful_report])),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3}), descriptor={'name': 'C'},
                      refresh=Mock(return_value=[successful_report])),
        }

        mock_load.return_value = sources
        conduit = content_controller.ContentSourcesConduit('task_id')
        step = content_controller.ContentSourcesRefreshStep(conduit)
        self.assertRaises(Exception, step.process)
        self.assertEquals(step.progress_successes, 0)
        self.assertEqual(step.progress_failures, 1)


class TestContentSourcesConduit(TestCase):

    def test_str(self):
        conduit = content_controller.ContentSourcesConduit('task-id-random')
        self.assertEqual(str(conduit), 'ContentSourcesConduit')


class TestQueueDownloadDeferred(TestCase):

    @patch(MODULE_PATH + 'pulp_tags')
    @patch(MODULE_PATH + 'download_deferred')
    def test_queue_download_deferred(self, mock_download_deferred, mock_tags):
        """Assert download_deferred tasks are tagged correctly."""
        content_controller.queue_download_deferred()
        mock_tags.action_tag.assert_called_once_with(mock_tags.ACTION_DEFERRED_DOWNLOADS_TYPE)
        mock_download_deferred.apply_async.assert_called_once_with(
            tags=[mock_tags.action_tag.return_value]
        )


class TestQueueDownloadRepo(TestCase):

    @patch(MODULE_PATH + 'pulp_tags')
    @patch(MODULE_PATH + 'download_repo')
    def test_queue_download_repo(self, mock_download_repo, mock_tags):
        """Assert download_repo tasks are tagged correctly."""
        content_controller.queue_download_repo('fake-id')
        mock_tags.resource_tag.assert_called_once_with(
            mock_tags.RESOURCE_REPOSITORY_TYPE,
            'fake-id'
        )
        mock_tags.action_tag.assert_called_once_with(mock_tags.ACTION_DOWNLOAD_TYPE)
        mock_download_repo.apply_async.assert_called_once_with(
            ['fake-id'],
            {'verify_all_units': False},
            tags=[mock_tags.resource_tag.return_value, mock_tags.action_tag.return_value]
        )


class TestDownloadDeferred(TestCase):

    @patch(MODULE_PATH + 'LazyUnitDownloadStep')
    @patch(MODULE_PATH + '_create_download_requests')
    @patch(MODULE_PATH + '_get_deferred_content_units')
    def test_download_deferred(self, mock_get_deferred, mock_create_requests, mock_step):
        """Assert the download step is initialized and called."""
        content_controller.download_deferred()
        mock_create_requests.assert_called_once_with(mock_get_deferred.return_value)
        mock_step.return_value.process_lifecycle.assert_called_once_with()


class TestDownloadRepo(TestCase):

    @patch(MODULE_PATH + 'LazyUnitDownloadStep')
    @patch(MODULE_PATH + '_create_download_requests')
    @patch(MODULE_PATH + 'repo_controller.find_units_not_downloaded')
    def test_download_repo_no_verify(self, mock_missing_units, mock_create_requests, mock_step):
        """Assert the download step is initialized and called with missing units."""
        content_controller.download_repo('fake-id')
        mock_missing_units.assert_called_once_with('fake-id')
        mock_create_requests.assert_called_once_with(mock_missing_units.return_value)
        mock_step.return_value.process_lifecycle.assert_called_once_with()

    @patch(MODULE_PATH + 'LazyUnitDownloadStep')
    @patch(MODULE_PATH + '_create_download_requests')
    @patch(MODULE_PATH + 'repo_controller.get_mongoengine_unit_querysets')
    def test_download_repo_verify(self, mock_units_qs, mock_create_requests, mock_step):
        """Assert the download step is initialized and called with all units."""
        mock_units_qs.return_value = [['some'], ['lists']]
        content_controller.download_repo('fake-id', verify_all_units=True)
        mock_units_qs.assert_called_once_with('fake-id')
        self.assertEqual(list(mock_create_requests.call_args[0][0]), ['some', 'lists'])
        mock_step.return_value.process_lifecycle.assert_called_once_with()


class TestGetDeferredContentUnits(TestCase):

    @patch(MODULE_PATH + 'plugin_api.get_unit_model_by_id')
    @patch(MODULE_PATH + 'DeferredDownload')
    def test_get_deferred_content_units(self, mock_qs, mock_get_model):
        # Setup
        mock_unit = Mock(unit_type_id='abc', unit_id='123')
        mock_qs.objects.filter.return_value = [mock_unit]

        # Test
        result = list(content_controller._get_deferred_content_units())
        self.assertEqual(1, len(result))
        mock_get_model.assert_called_once_with('abc')
        unit_filter = mock_get_model.return_value.objects.filter
        unit_filter.assert_called_once_with(id='123')
        unit_filter.return_value.get.assert_called_once_with()

    @patch(MODULE_PATH + '_logger.error')
    @patch(MODULE_PATH + 'plugin_api.get_unit_model_by_id')
    @patch(MODULE_PATH + 'DeferredDownload')
    def test_get_deferred_content_units_no_model(self, mock_qs, mock_get_model, mock_log):
        # Setup
        mock_unit = Mock(unit_type_id='abc', unit_id='123')
        mock_qs.objects.filter.return_value = [mock_unit]
        mock_get_model.return_value = None

        # Test
        result = list(content_controller._get_deferred_content_units())
        self.assertEqual(0, len(result))
        mock_log.assert_called_once_with('Unable to find the model object for the abc type.')
        mock_get_model.assert_called_once_with('abc')

    @patch(MODULE_PATH + '_logger.debug')
    @patch(MODULE_PATH + 'plugin_api.get_unit_model_by_id')
    @patch(MODULE_PATH + 'DeferredDownload')
    def test_get_deferred_content_units_no_unit(self, mock_qs, mock_get_model, mock_log):
        # Setup
        mock_unit = Mock(unit_type_id='abc', unit_id='123')
        mock_qs.objects.filter.return_value = [mock_unit]
        unit_qs = mock_get_model.return_value.objects.filter.return_value
        unit_qs.get.side_effect = DoesNotExist

        # Test
        result = list(content_controller._get_deferred_content_units())
        self.assertEqual(0, len(result))
        mock_log.assert_called_once_with('Unable to find the abc:123 content unit.')
        mock_get_model.assert_called_once_with('abc')


class TestCreateDownloadRequests(TestCase):

    @patch(MODULE_PATH + 'Key.load', Mock())
    @patch(MODULE_PATH + 'get_working_directory', Mock(return_value='/working/'))
    @patch(MODULE_PATH + 'mkdir')
    @patch(MODULE_PATH + '_get_streamer_url')
    @patch(MODULE_PATH + 'LazyCatalogEntry')
    def test_create_download_requests(self, mock_catalog, mock_get_url, mock_mkdir):
        # Setup
        content_units = [Mock(id='123', type_id='abc', list_files=lambda: ['/file/path'])]
        filtered_qs = mock_catalog.objects.filter.return_value
        catalog_entry = filtered_qs.order_by.return_value.first.return_value
        catalog_entry.path = '/storage/123/path'
        expected_data_dict = {
            content_controller.TYPE_ID: 'abc',
            content_controller.UNIT_ID: '123',
            content_controller.UNIT_FILES: {
                '/working/123/path': {
                    content_controller.CATALOG_ENTRY: catalog_entry,
                    content_controller.PATH_DOWNLOADED: None
                }
            }
        }

        # Test
        requests = content_controller._create_download_requests(content_units)
        mock_catalog.objects.filter.assert_called_once_with(
            unit_id='123',
            unit_type_id='abc',
            path='/file/path'
        )
        filtered_qs.order_by.assert_called_once_with('revision')
        filtered_qs.order_by.return_value.first.assert_called_once_with()
        mock_mkdir.assert_called_once_with('/working/123')
        self.assertEqual(1, len(requests))
        self.assertEqual(mock_get_url.return_value, requests[0].url)
        self.assertEqual('/working/123/path', requests[0].destination)
        self.assertEqual(expected_data_dict, requests[0].data)


class TestGetStreamerUrl(TestCase):

    def setUp(self):
        self.catalog = Mock(path='/path/to/content')
        self.config = {
            'https_retrieval': 'true',
            'redirect_host': 'pulp.example.com',
            'redirect_port': '',
            'redirect_path': '/streamer/'
        }

    @patch(MODULE_PATH + 'pulp_conf')
    @patch(MODULE_PATH + 'URL')
    def test_https_url(self, mock_url, mock_conf):
        """Assert HTTPS URLs are made if configured."""
        expected_unsigned_url = 'https://pulp.example.com/streamer/path/to/content'
        mock_key = Mock()
        mock_conf.get = lambda s, k: self.config[k]

        url = content_controller._get_streamer_url(self.catalog, mock_key)
        mock_url.assert_called_once_with(expected_unsigned_url)
        mock_url.return_value.sign.assert_called_once_with(
            mock_key, expiration=(60 * 60 * 24 * 365))
        signed_url = mock_url.return_value.sign.return_value
        self.assertEqual(url, str(signed_url))

    @patch(MODULE_PATH + 'pulp_conf')
    @patch(MODULE_PATH + 'URL')
    def test_http_url(self, mock_url, mock_conf):
        """Assert HTTP URLs are made if configured."""
        expected_unsigned_url = 'http://pulp.example.com/streamer/path/to/content'
        mock_key = Mock()
        mock_conf.get = lambda s, k: self.config[k]
        self.config['https_retrieval'] = 'false'

        content_controller._get_streamer_url(self.catalog, mock_key)
        mock_url.assert_called_once_with(expected_unsigned_url)

    @patch(MODULE_PATH + 'pulp_conf')
    @patch(MODULE_PATH + 'URL')
    def test_url_unparsable_setting(self, mock_url, mock_conf):
        """Assert an exception is raised if the configuration is unparsable."""
        mock_conf.get = lambda s, k: self.config[k]
        self.config['https_retrieval'] = 'unsure'

        self.assertRaises(
            PulpCodedTaskException,
            content_controller._get_streamer_url,
            self.catalog,
            Mock(),
        )

    @patch(MODULE_PATH + 'pulp_conf')
    @patch(MODULE_PATH + 'URL')
    def test_explicit_port(self, mock_url, mock_conf):
        """Assert URLs are correctly formed with ports."""
        expected_unsigned_url = 'https://pulp.example.com:1234/streamer/path/to/content'
        mock_key = Mock()
        mock_conf.get = lambda s, k: self.config[k]
        self.config['redirect_port'] = '1234'

        content_controller._get_streamer_url(self.catalog, mock_key)
        mock_url.assert_called_once_with(expected_unsigned_url)


class TestLazyStatusConduit(TestCase):

    def test_creation(self):
        """Assert the conduit is initialized correctly."""
        conduit = content_controller.LazyStatusConduit('fake-id')
        self.assertEqual('fake-id', conduit.report_id)
        self.assertEqual(LazyStatusConduitException, conduit.exception_class)

    def test_str(self):
        """Assert __str__ is defined on the conduit."""
        conduit = content_controller.LazyStatusConduit('fake-id')
        self.assertEqual('LazyStatusConduit', str(conduit))


class TestLazyUnitDownloadStep(TestCase):

    def setUp(self):
        self.step = content_controller.LazyUnitDownloadStep(
            'test_step',
            'Test Step',
            content_controller.LazyStatusConduit('fake-id'),
            [Mock()]
        )
        self.data = {
            content_controller.TYPE_ID: 'abc',
            content_controller.UNIT_ID: '1234',
            content_controller.UNIT_FILES: {
                '/no/where': {
                    content_controller.CATALOG_ENTRY: Mock(),
                    content_controller.PATH_DOWNLOADED: None
                }
            }
        }
        self.report = Mock(data=self.data, destination='/no/where')

    def test_process_block(self):
        """Assert calls to `_process_block` result in calls to the downloader."""
        self.step.downloader = Mock()
        self.step._process_block()
        self.step.downloader.download.assert_called_once_with(self.step.download_requests)

    def test_get_total(self):
        """Assert total is equal to the length of the download request list."""
        self.assertEqual(1, self.step.get_total())

    @patch(MODULE_PATH + 'DeferredDownload')
    def test_download_started(self, mock_deferred_download):
        """Assert if validate_file raises an exception, the download is not skipped."""
        self.step.validate_file = Mock(side_effect=IOError)

        # Test that deferred download entry for the unit.
        self.step.download_started(self.report)
        qs = mock_deferred_download.objects.filter
        qs.assert_called_once_with(unit_id='1234', unit_type_id='abc')
        qs.return_value.delete.assert_called_once_with()

    @patch(MODULE_PATH + 'DeferredDownload')
    def test_download_started_already_downloaded(self, mock_deferred_download):
        """Assert if validate_file doesn't raise an exception, the download is skipped."""
        self.step.validate_file = Mock()

        # Test that deferred download entry for the unit.
        self.assertRaises(
            content_controller.SkipLocation,
            self.step.download_started,
            self.report
        )
        qs = mock_deferred_download.objects.filter
        qs.assert_called_once_with(unit_id='1234', unit_type_id='abc')
        qs.return_value.delete.assert_called_once_with()

    @patch(MODULE_PATH + 'os.path.relpath', Mock(return_value='filename'))
    @patch(MODULE_PATH + 'plugin_api.get_unit_model_by_id')
    def test_download_succeeded(self, mock_get_model):
        """Assert single file units mark the unit downloaded."""
        # Setup
        self.step.validate_file = Mock()
        model_qs = mock_get_model.return_value
        unit = model_qs.objects.filter.return_value.only.return_value.get.return_value

        # Test
        self.step.download_succeeded(self.report)
        unit.set_storage_path.assert_called_once_with('filename')
        self.assertEqual(
            {'set___storage_path': unit._storage_path},
            model_qs.objects.filter.return_value.update_one.call_args_list[0][1]
        )
        unit.import_content.assert_called_once_with(self.report.destination)
        self.assertEqual(1, self.step.progress_successes)
        self.assertEqual(0, self.step.progress_failures)
        self.assertEqual(
            {'set__downloaded': True},
            model_qs.objects.filter.return_value.update_one.call_args_list[1][1]
        )

    @patch(MODULE_PATH + 'os.path.relpath', Mock(return_value='a/filename'))
    @patch(MODULE_PATH + 'plugin_api.get_unit_model_by_id')
    def test_download_succeeded_multifile(self, mock_get_model):
        """Assert multi-file units are not marked as downloaded on single file completion."""
        # Setup
        self.step.validate_file = Mock()
        model_qs = mock_get_model.return_value
        unit = model_qs.objects.filter.return_value.only.return_value.get.return_value
        self.data[content_controller.UNIT_FILES]['/second/file'] = {
            content_controller.PATH_DOWNLOADED: None
        }

        # Test
        self.step.download_succeeded(self.report)
        self.assertEqual(0, unit.set_storage_path.call_count)
        unit.import_content.assert_called_once_with(
            self.report.destination,
            location='a/filename'
        )
        self.assertEqual(1, self.step.progress_successes)
        self.assertEqual(0, self.step.progress_failures)
        self.assertEqual(0, model_qs.objects.filter.return_value.update_one.call_count)

    @patch(MODULE_PATH + 'os.path.relpath', Mock(return_value='a/filename'))
    @patch(MODULE_PATH + 'plugin_api.get_unit_model_by_id')
    def test_download_succeeded_multifile_last_file(self, mock_get_model):
        """Assert multi-file units are marked as downloaded on last file completion."""
        # Setup
        self.step.validate_file = Mock()
        model_qs = mock_get_model.return_value
        unit = model_qs.objects.filter.return_value.only.return_value.get.return_value
        self.data[content_controller.UNIT_FILES]['/second/file'] = {
            content_controller.PATH_DOWNLOADED: True
        }

        # Test
        self.step.download_succeeded(self.report)
        self.assertEqual(0, unit.set_storage_path.call_count)
        unit.import_content.assert_called_once_with(
            self.report.destination,
            location='a/filename'
        )
        self.assertEqual(1, self.step.progress_successes)
        self.assertEqual(0, self.step.progress_failures)
        model_qs.objects.filter.return_value.update_one.assert_called_once_with(
            set__downloaded=True)

    @patch(MODULE_PATH + 'os.path.relpath', Mock(return_value='filename'))
    @patch(MODULE_PATH + 'plugin_api.get_unit_model_by_id')
    def test_download_succeeded_corrupted_download(self, mock_get_model):
        """Assert corrupted downloads are not copied or marked as downloaded."""
        # Setup
        self.step.validate_file = Mock(side_effect=content_controller.VerificationException)
        model_qs = mock_get_model.return_value
        unit = model_qs.objects.filter.return_value.only.return_value.get.return_value

        # Test
        self.step.download_succeeded(self.report)
        self.assertEqual(0, unit.set_storage_path.call_count)
        self.assertEqual(0, unit.import_content.call_count)
        self.assertEqual(0, self.step.progress_successes)
        self.assertEqual(1, self.step.progress_failures)

    def test_download_failed(self):
        self.assertEqual(0, self.step.progress_failures)
        self.step.download_failed(self.report)
        self.assertEqual(1, self.step.progress_failures)
        path_entry = self.report.data[content_controller.UNIT_FILES]['/no/where']
        self.assertFalse(path_entry[content_controller.PATH_DOWNLOADED])

    @patch('__builtin__.open')
    @patch(MODULE_PATH + 'verify_checksum')
    def test_validate_file(self, mock_verify_checksum, mock_open):
        self.step.validate_file('/no/where', 'sha8', '7')
        self.assertEqual(('sha8', '7'), mock_verify_checksum.call_args[0][1:])
        mock_open.assert_called_once_with('/no/where')

    @patch(MODULE_PATH + 'verify_checksum')
    def test_validate_file_fail(self, mock_verify_checksum):
        mock_verify_checksum.side_effect = IOError
        self.assertRaises(IOError, self.step.validate_file, '/no/where', 'sha8', '7')

    @patch(MODULE_PATH + 'os.path.isfile')
    def test_validate_file_no_checksum(self, mock_isfile):
        mock_isfile.return_value = False
        self.assertRaises(IOError, self.step.validate_file, '/no/where', None, None)
