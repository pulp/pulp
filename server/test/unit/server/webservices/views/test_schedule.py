import unittest

import mock

from pulp.server import exceptions as pulp_exceptions
from pulp.server.webservices.views import schedule


class TestScheduleResource(unittest.TestCase):
    """
    Tests for ScheduleResource.
    """

    @mock.patch('pulp.server.webservices.views.schedule.schedule_utils.get')
    @mock.patch('pulp.server.webservices.views.schedule.generate_json_response')
    def test__get(self, mock_resp, mock_sched_list):
        """
        Test _get under expected conditions.
        """
        mock_sched = mock.MagicMock()
        mock_sched.for_display.return_value = {'id': 'mock_sched'}
        mock_sched_list.return_value = [mock_sched]
        response = schedule.ScheduleResource()._get('mock_schedule', '/mock/path/')

        mock_resp.assert_called_once_with({'id': 'mock_sched', '_href': '/mock/path/'})
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.schedule.schedule_utils.get')
    def test__get_missing_schedule_id(self, mock_sched_list):
        """
        If schedule_utils.get returns an empty list, raise a MissingResource.
        """
        mock_sched_list.return_value = []

        try:
            schedule.ScheduleResource()._get('mock_schedule', '/mock/path/')
        except pulp_exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError('MissingResource should be raised if schedule does not exist')

        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'schedule_id': 'mock_schedule'})

    @mock.patch('pulp.server.webservices.views.schedule.schedule_utils.get')
    def test__get_invalid_schedule_id(self, mock_sched_list):
        """
        MissingResource should also be raised even if schedule_id is not valid bson ObjectID.
        """
        mock_sched_list.side_effect = pulp_exceptions.InvalidValue('Not a valid bson ObjectID')

        try:
            schedule.ScheduleResource()._get('mock_schedule', '/mock/path/')
        except pulp_exceptions.MissingResource, response:
            pass
        else:
            raise AssertionError('MissingResource should be raised if schedule is invalid')

        self.assertEqual(response.http_status_code, 404)
        self.assertEqual(response.error_data['resources'], {'schedule_id': 'mock_schedule'})
