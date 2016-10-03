import unittest

import mock

from pulp.bindings.responses import Task
from pulp.client.commands.consumer import content as consumer_content


# We can't use the standard json lib from pulp.server.compat
# because pulp.server.compat can not be imported with python 2.4
try:
    import json as _json
except ImportError:
    import simplejson as _json

json = _json


class InstantiationTests(unittest.TestCase):

    def setUp(self):
        self.mock_context = mock.MagicMock()
        self.action = 'action'

    def tearDown(self):
        self.mock_context = mock.MagicMock()

    def test_progress_tracker(self):
        try:
            consumer_content.ConsumerContentProgressTracker(self.mock_context.prompt)
        except Exception, e:
            self.fail(str(e))

    def test_schedules_section(self):
        try:
            consumer_content.ConsumerContentSchedulesSection(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_list_schedule(self):
        try:
            consumer_content.ConsumerContentListScheduleCommand(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_create_schedule(self):
        try:
            consumer_content.ConsumerContentCreateScheduleCommand(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_delete_schedule(self):
        try:
            consumer_content.ConsumerContentDeleteScheduleCommand(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_update_schedule(self):
        try:
            consumer_content.ConsumerContentUpdateScheduleCommand(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_next_run(self):
        try:
            consumer_content.ConsumerContentNextRunCommand(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))

    def test_schedules_strategy(self):
        try:
            consumer_content.ConsumerContentScheduleStrategy(self.mock_context, self.action)
        except Exception, e:
            self.fail(str(e))


POSTPONED_TASK = Task({'call_request_id': '1',
                       'call_request_group_id': None,
                       'call_request_tags': [],
                       'start_time': None,
                       'finish_time': None,
                       'response': 'postponed',
                       'reasons': [],
                       'state': 'waiting',
                       'progress': {},
                       'result': None,
                       'exception': None,
                       'traceback': None})
