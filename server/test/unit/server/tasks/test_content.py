# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import sys
from unittest import TestCase
from mock import patch, Mock, call

from pulp.server.tasks.content import ContentSourcesRefreshStep, ContentSourcesConduit
from pulp.server.exceptions import PulpCodedTaskFailedException


class TestContentSourcesRefreshStep(TestCase):

    @patch('pulp.server.tasks.content.ContentSourcesRefreshStep.process_main')
    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_process_main_one(self, mock_load, mock_process_main):
        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1})),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2})),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3})),
        }

        mock_load.return_value = sources
        conduit = ContentSourcesConduit('task_id')
        step = ContentSourcesRefreshStep(conduit, content_source_id='C')
        step.process()
        step.process_main.assert_called_with(item=sources['C'])
        self.assertEquals(step.progress_successes, 1)

    @patch('pulp.server.tasks.content.ContentSourcesRefreshStep.process_main')
    @patch('pulp.server.content.sources.model.ContentSource.load_all')
    def test_process_main_all(self, mock_load, mock_process_main):
        sources = {
            'A': Mock(id='A', dict=Mock(return_value={'A': 1})),
            'B': Mock(id='B', dict=Mock(return_value={'B': 2})),
            'C': Mock(id='C', dict=Mock(return_value={'C': 3})),
        }

        mock_load.return_value = sources
        conduit = ContentSourcesConduit('task_id')
        step = ContentSourcesRefreshStep(conduit)
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
        conduit = ContentSourcesConduit('task_id')
        step = ContentSourcesRefreshStep(conduit)
        self.assertRaises(PulpCodedTaskFailedException, step.process)
        self.assertEquals(step.progress_successes, 2)
        self.assertEqual(step.progress_failures, 1)

    @patch('pulp.server.tasks.content.ContentSourcesRefreshStep.process_main',
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
        conduit = ContentSourcesConduit('task_id')
        step = ContentSourcesRefreshStep(conduit)
        self.assertRaises(Exception, step.process)
        self.assertEquals(step.progress_successes, 0)
        self.assertEqual(step.progress_failures, 1)

class TestContentSourcesConduit(TestCase):

    def test_str(self):
        conduit = ContentSourcesConduit('task-id-random')
        self.assertEqual(str(conduit), 'ContentSourcesConduit')