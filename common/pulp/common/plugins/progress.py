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
Contains classes and functions related to tracking the progress of the
importer and distributor.
"""
from datetime import datetime
from gettext import gettext as _

from pulp.common.dateutils import format_iso8601_datetime, parse_iso8601_datetime


class ProgressReport(object):
    """
    This class is not meant to be instantiated directly, but has some common methods that are
    used by the Sync and Progress report objects.
    """
    # The following states can be set using the state() property
    # This is the starting state, before the sync or publish begins
    STATE_NOT_STARTED = 'not_started'
    # When everything is done
    STATE_COMPLETE = 'complete'
    # If an error occurs outside in progress states, this general failed state can be set
    STATE_FAILED = 'failed'
    # When the user has cancelled a sync
    STATE_CANCELED = 'cancelled'

    def __init__(self, conduit=None, state=None, state_times=None, error_message=None,
                 traceback=None):
        """
        Initialize the ProgressReport. All parameters except conduit can be ignored if you are
        instantiating the report for use from an importer or distributor. The other parameters
        are used when instantiating the report from a serialized report in the client.

        :param conduit:            A sync or publish conduit that should be used to report progress
                                   to the client.
        :type  conduit:            pulp.plugins.conduits.repo_sync.RepoSyncConduit or
                                   pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param state:              The state the ProgressReport should be initialized to. See the
                                   STATE_* class variables for valid states.
        :type  state:              basestring
        :param state_times:        A dictionary mapping state names to the time the report entered
                                   that state
        :type  state_times:        dict of states to utc datetime values
        :param error_message:      A general error message. This is used when the error encountered
                                   was not specific to any particular content unit
        :type  error_message:      basestring
        :param traceback:          If there was a traceback associated with an error_message, it
                                   should be included here
        :type  traceback:          basestring
        """
        self.conduit = conduit

        if state is None:
            self._state = self.STATE_NOT_STARTED
        else:
            self._state = state

        # This is a mapping of state names to the time that state was entered, in UTC.
        if state_times is None:
            self.state_times = {self.STATE_NOT_STARTED: datetime.utcnow()}
        else:
            self.state_times = state_times

        # overall execution error
        self.error_message = error_message
        self.traceback = traceback

    def build_final_report(self):
        """
        Assembles the final report to return to Pulp at the end of the run.

        :return: report to return to Pulp at the end of the publish or sync call
        :rtype:  pulp.plugins.model.PublishReport or pulp.plugins.model.SyncReport
        """
        # intentionally empty; not sure what to put in here
        summary = self.build_progress_report()
        details = None

        if self.state in (self.STATE_COMPLETE, self.STATE_CANCELED):
            report = self.conduit.build_success_report(summary, details)
        else:
            report = self.conduit.build_failure_report(summary, details)

        return report

    def build_progress_report(self):
        """
        Returns the actual report that should be sent to Pulp as the current
        progress of the sync.

        :return: description of the current state of the sync
        :rtype:  dict
        """
        report = {
            'state': self.state,
            'state_times': {},
            'error_message': self.error_message,
            'traceback': self.traceback,
        }
        # Let's convert the state transition times to a serializable format
        for key, value in self.state_times.items():
            report['state_times'][key] = format_iso8601_datetime(value)
        return report

    @classmethod
    def from_progress_report(cls, report):
        """
        Parses the output from the build_progress_report method into an instance
        of this class. The intention is to use this client-side to reconstruct
        the instance as it is retrieved from the server.

        The build_final_report call on instances returned from this call will
        not function as it requires the server-side conduit to be provided.
        Additionally, any exceptions and tracebacks will be a text representation
        instead of formal objects.

        :param report: progress report retrieved from the server's task
        :type  report: dict
        :return:       instance populated with the state in the report
        :rtype:        ProgressReport
        """
        # Restore the state transition times to datetime objects
        for key, value in report['state_times'].items():
            report['state_times'][key] = parse_iso8601_datetime(value)
        r = cls(None, **report)
        return r

    def update_progress(self):
        """
        Sends the current state of the progress report to Pulp.
        """
        report = self.build_progress_report()
        self.conduit.set_progress(report)

    def _get_state(self):
        """
        This is used to provide the state property, and returns the current _state attribute.
        :return : The string representation of the current state
        :rtype : str
        """
        return self._state

    def _set_state(self, new_state):
        """
        This method allows users to set a new state to the ProgressReport. It enforces state
        transitions to only happen in a certain fashion.

        :param new_state: The new state that the caller wishes the ProgressReport to be set to
        :type  new_state: basestring
        """
        if new_state == self._state:
            # setting the state to curent state is strange, but we'll let it slide without error
            return

        # Enforce our state transition mapping
        if new_state not in self.ALLOWED_STATE_TRANSITIONS[self._state]:
            err_msg = _('State transition not allowed: %(state)s --> %(new_state)s')
            err_msg = err_msg % {'state': self._state, 'new_state': new_state}
            raise ValueError(err_msg)

        # Set the state, and also note what time we reached that state
        self._state = new_state
        self.state_times[new_state] = datetime.utcnow()
        self.update_progress()

    state = property(_get_state, _set_state)
