# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
The tests in this module test the pulp.common.progress module.
"""

from datetime import datetime
import unittest

import mock
from pulp.plugins.model import PublishReport
from pulp.plugins.conduits.repo_sync import RepoSyncConduit

from pulp.common.dateutils import format_iso8601_datetime
from pulp.common.plugins import progress


class TestProgressReport(unittest.TestCase):

    """
    Test the ProgressReport class.
    """
    def setUp(self):
        self.conduit = get_mock_conduit()

    def test___init___with_defaults(self):
        """
        Test the __init__ method with all default parameters.
        """
        report = progress.ProgressReport()

        # Make sure all the appropriate attributes were set
        self.assertEqual(report.conduit, None)
        self.assertEqual(report._state, progress.ProgressReport.STATE_NOT_STARTED)

        # The state_times attribute should be a dictionary with only the time the not started state was
        # entered
        self.assertTrue(isinstance(report.state_times, dict))
        self.assertEqual(len(report.state_times), 1)
        self.assertTrue(isinstance(report.state_times[progress.ProgressReport.STATE_NOT_STARTED],
                                   datetime))

        self.assertEqual(report.error_message, None)
        self.assertEqual(report.traceback, None)

    def test___init__with_non_defaults(self):
        """
        Test the __init__ method when passing in parameters.
        """
        state = progress.ProgressReport.STATE_FAILED
        state_times = {progress.ProgressReport.STATE_FAILED: datetime.utcnow()}
        error_message = 'This is an error message.'
        traceback = 'This is a traceback.'

        report = progress.ProgressReport(
            self.conduit, state=state, state_times=state_times,
            error_message=error_message, traceback=traceback)

        # Make sure all the appropriate attributes were set
        self.assertEqual(report.conduit, self.conduit)
        self.assertEqual(report._state, state)
        self.assertEqual(report.state_times, state_times)
        self.assertEqual(report.error_message, error_message)
        self.assertEqual(report.traceback, traceback)

    def test_build_final_report_failure(self):
        """
        Test build_final_report() when there is a failure.
        """
        report = progress.ProgressReport(self.conduit, state=progress.ProgressReport.STATE_FAILED)

        conduit_report = report.build_final_report()

        # The success report call should not have been made
        self.assertEqual(self.conduit.build_success_report.call_count, 0)
        # We should have called the failure report once with the serialized progress report as the summary
        self.conduit.build_failure_report.assert_called_once_with(report.build_progress_report(), None)

        # Inspect the conduit report
        self.assertEqual(conduit_report.success_flag, False)
        self.assertEqual(conduit_report.canceled_flag, False)
        self.assertEqual(conduit_report.summary, report.build_progress_report())
        self.assertEqual(conduit_report.details, None)

    def test_build_final_report_success(self):
        """
        Test build_final_report() when there is success.
        """
        report = progress.ProgressReport(self.conduit, state=progress.ProgressReport.STATE_COMPLETE)

        conduit_report = report.build_final_report()

        # The failure report call should not have been made
        self.assertEqual(self.conduit.build_failure_report.call_count, 0)
        # We should have called the success report once with the serialized progress report as the summary
        self.conduit.build_success_report.assert_called_once_with(report.build_progress_report(), None)

        # Inspect the conduit report
        self.assertEqual(conduit_report.success_flag, True)
        self.assertEqual(conduit_report.canceled_flag, False)
        self.assertEqual(conduit_report.summary, report.build_progress_report())
        self.assertEqual(conduit_report.details, None)

    def test_build_final_report_cancelled(self):
        """
        Test build_final_report() when the state is cancelled. Since the user asked for it to be
        cancelled, we should report it as a success
        """
        report = progress.ProgressReport(self.conduit,
                                            state=progress.ProgressReport.STATE_CANCELED)

        conduit_report = report.build_final_report()

        # The failure report call should not have been made
        self.assertEqual(self.conduit.build_failure_report.call_count, 0)
        # We should have called the success report once with the serialized progress report as the
        # summary
        self.conduit.build_success_report.assert_called_once_with(report.build_progress_report(),
                                                                  None)

        # Inspect the conduit report
        self.assertEqual(conduit_report.success_flag, True)
        self.assertEqual(conduit_report.canceled_flag, False)
        self.assertEqual(conduit_report.summary, report.build_progress_report())
        self.assertEqual(conduit_report.details, None)

    def test_build_progress_report(self):
        """
        Test the build_progress_report() method.
        """
        state = progress.ProgressReport.STATE_FAILED
        state_times = {progress.ProgressReport.STATE_FAILED: datetime.utcnow()}
        error_message = 'This is an error message.'
        traceback = 'This is a traceback.'
        report = progress.ProgressReport(
            self.conduit, state=state, state_times=state_times,
            error_message=error_message, traceback=traceback)

        report = report.build_progress_report()

        # Make sure all the appropriate attributes were set
        self.assertEqual(report['state'], state)
        expected_state_times = {}
        for key, value in state_times.items():
            expected_state_times[key] = format_iso8601_datetime(value)
        self.assertTrue(report['state_times'], expected_state_times)
        self.assertEqual(report['error_message'], error_message)
        self.assertEqual(report['traceback'], traceback)

    def test_from_progress_report(self):
        """
        Test that building an ProgressReport from the output of build_progress_report() makes an equivalent
        ProgressReport.
        """
        state = progress.ProgressReport.STATE_FAILED
        state_times = {progress.ProgressReport.STATE_FAILED: datetime(2013, 5, 3, 20, 11, 3)}
        error_message = 'This is an error message.'
        traceback = 'This is a traceback.'
        original_report = progress.ProgressReport(
            self.conduit, state=state, state_times=state_times,
            error_message=error_message, traceback=traceback)
        serial_report = original_report.build_progress_report()

        report = progress.ProgressReport.from_progress_report(serial_report)

        # All of the values that we had set in the initial report should be identical on this one, except that
        # the conduit should be None
        self.assertEqual(report.conduit, None)
        self.assertEqual(report._state, original_report.state)
        self.assertEqual(report.state_times, original_report.state_times)
        self.assertEqual(report.error_message, original_report.error_message)
        self.assertEqual(report.traceback, original_report.traceback)

    def test_update_progress(self):
        """
        The update_progress() method should send the progress report to the conduit.
        """
        state = progress.ProgressReport.STATE_FAILED
        state_times = {progress.ProgressReport.STATE_FAILED: datetime.utcnow()}
        error_message = 'This is an error message.'
        traceback = 'This is a traceback.'
        report = progress.ProgressReport(
            self.conduit, state=state, state_times=state_times,
            error_message=error_message, traceback=traceback)

        report.update_progress()

        # Make sure the conduit's set_progress() method was called
        self.conduit.set_progress.assert_called_once_with(report.build_progress_report())

    def test__get_state(self):
        """
        Test our state property as a getter.
        """
        report = progress.ProgressReport(None, state=progress.ProgressReport.STATE_COMPLETE)

        self.assertEqual(report.state, progress.ProgressReport.STATE_COMPLETE)

    # Normally, the ProgressReport doesn't have ALLOWED_STATE_TRANSITIONS, so let's give it one for this
    # test
    @mock.patch('pulp.common.plugins.progress.ProgressReport.ALLOWED_STATE_TRANSITIONS',
                {'state_1': ['state_2']}, create=True)
    def test__set_state_allowed_transition(self):
        """
        Test the state property as a setter for an allowed state transition.
        """
        report = progress.ProgressReport(self.conduit, state='state_1')

        # This is an allowed transition, so it should not raise an error
        report.state = 'state_2'

        self.assertEqual(report._state, 'state_2')
        self.assertTrue(report._state in report.state_times)
        self.assertTrue(isinstance(report.state_times[report._state], datetime))
        self.conduit.set_progress.assert_called_once_with(report.build_progress_report())

    # Normally, the ProgressReport doesn't have ALLOWED_STATE_TRANSITIONS, so let's give it one for this
    # test
    @mock.patch('pulp.common.plugins.progress.ProgressReport.ALLOWED_STATE_TRANSITIONS',
                {'state_1': ['state_2']}, create=True)
    def test__set_state_disallowed_transition(self):
        """
        Test the state property as a setter for a disallowed state transition.
        """
        report = progress.ProgressReport(None, state='state_1')

        # We can't go from state_1 to anything other than state_2
        try:
            report.state = 'state_3'
            self.fail('The line above this should have raised an Exception, but it did not.')
        except ValueError, e:
            expected_error_substring = '%s --> %s' % (report.state, 'state_3')
            self.assertTrue(expected_error_substring in str(e))

        # The state should remain the same
        self.assertEqual(report.state, 'state_1')
        self.assertTrue('state_3' not in report.state_times)

    # Normally, the ProgressReport doesn't have ALLOWED_STATE_TRANSITIONS, so let's give it one for this
    # test
    @mock.patch('pulp.common.plugins.progress.ProgressReport.ALLOWED_STATE_TRANSITIONS',
                {'state_1': ['state_2']}, create=True)
    def test__set_state_same_state(self):
        """
        Test setting a state to the same state. This is weird, but allowed.
        """
        report = progress.ProgressReport(None, state='state_1')

        # This should not raise an Exception
        report.state = 'state_1'

        self.assertEqual(report.state, 'state_1')



def get_mock_conduit(type_id=None, existing_units=None, pkg_dir=None):
    def build_failure_report(summary, details):
        return PublishReport(False, summary, details)

    def build_success_report(summary, details):
        return PublishReport(True, summary, details)
    """
    def side_effect(type_id, key, metadata, rel_path):
        if rel_path and pkg_dir:
            rel_path = os.path.join(pkg_dir, rel_path)
            if not os.path.exists(os.path.dirname(rel_path)):
                os.makedirs(os.path.dirname(rel_path))
        unit = Unit(type_id, key, metadata, rel_path)
        return unit

    def get_units(criteria=None):
        ret_val = []
        if existing_units:
            for u in existing_units:
                if criteria:
                    if u.type_id in criteria.type_ids:
                        ret_val.append(u)
                else:
                    ret_val.append(u)
        return ret_val

    def search_all_units(type_id, criteria):
        ret_val = []
        if existing_units:
            for u in existing_units:
                if u.type_id == type_id:
                    if u.unit_key['id'] == criteria['filters']['id']:
                        ret_val.append(u)
        return ret_val
    """

    sync_conduit = mock.Mock(spec=RepoSyncConduit)
    #sync_conduit.init_unit.side_effect = side_effect
    #sync_conduit.get_units.side_effect = get_units
    sync_conduit.save_unit = mock.Mock()
    #sync_conduit.search_all_units.side_effect = search_all_units
    sync_conduit.build_failure_report = mock.MagicMock(side_effect=build_failure_report)
    sync_conduit.build_success_report = mock.MagicMock(side_effect=build_success_report)
    sync_conduit.set_progress = mock.MagicMock()

    return sync_conduit
