import unittest

from celery.result import AsyncResult
import mock

from pulp.server.webservices.middleware import postponed


class MockException(Exception):
    pass


class TestPostponedOperationMiddleware(unittest.TestCase):
    """
    Tests for the handling of async exceptions.
    """

    @mock.patch('pulp.server.webservices.middleware.postponed.json_util.default')
    @mock.patch('pulp.server.webservices.middleware.postponed.TaskResult')
    @mock.patch('pulp.server.webservices.middleware.postponed.json')
    def test_get_operation_postponed_async_body_dict(self, mjson, mtask_result, mjson_default):
        """
        Test handling of a AsyncResult call report.
        """
        e = MockException()
        mock_result = mock.MagicMock()
        del mock_result.serializer
        e.call_report = AsyncResult(mock.MagicMock())
        mock_task_result = mtask_result.from_async_result.return_value
        mock_serialized = {'result': mock_result, 'spawned_tasks': []}
        mock_task_result.serialize.return_value = mock_serialized
        ret = postponed.PostponedOperationMiddleware._get_operation_postponed_body(e)
        mtask_result.from_async_result.assert_called_once_with(e.call_report)
        mock_task_result.serialize.assert_called_once_with()
        mjson.dumps.assert_called_once_with(mock_serialized, default=mjson_default)
        self.assertTrue(ret is mjson.dumps.return_value)

    @mock.patch('pulp.server.webservices.middleware.postponed.json_util.default')
    @mock.patch('pulp.server.webservices.middleware.postponed.TaskResult')
    @mock.patch('pulp.server.webservices.middleware.postponed.json')
    def test_get_operation_postponed_not_async_body_old(self, mjson, mtask_result, mjson_default):
        """
        Test handling if the result of the call report is not a Mongoengine Document.
        """
        e = MockException()
        e.call_report = mock.MagicMock()
        mock_result = mock.MagicMock()
        del mock_result.serializer
        mock_serialized = {'result': mock_result, 'spawned_tasks': []}
        e.call_report.serialize.return_value = mock_serialized
        ret = postponed.PostponedOperationMiddleware._get_operation_postponed_body(e)
        e.call_report.serialize.assert_called_once_with()
        self.assertFalse(hasattr(mock_result, 'serializer'))
        mjson.dumps.assert_called_once_with(mock_serialized, default=mjson_default)
        self.assertTrue(ret is mjson.dumps.return_value)

    @mock.patch('pulp.server.webservices.middleware.postponed.json_util.default')
    @mock.patch('pulp.server.webservices.middleware.postponed.TaskResult')
    @mock.patch('pulp.server.webservices.middleware.postponed.json')
    def test_get_operation_postponed_not_async_body_doc(self, mjson, mtask_result, mjson_default):
        """
        Test handling if the result of the call report is a Mongoengine Document.
        """
        e = MockException()
        e.call_report = mock.MagicMock()
        mock_result = mock.MagicMock()
        mock_serialized = {'result': mock_result, 'spawned_tasks': []}
        e.call_report.serialize.return_value = mock_serialized
        ret = postponed.PostponedOperationMiddleware._get_operation_postponed_body(e)
        e.call_report.serialize.assert_called_once_with()
        mock_result.serializer.assert_called_once_with(mock_result)
        mjson.dumps.assert_called_once_with(mock_serialized, default=mjson_default)
        mock_serialized['result'] = mock_result.serializer.return_value.data
        self.assertTrue(ret is mjson.dumps.return_value)
