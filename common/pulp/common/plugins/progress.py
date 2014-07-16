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


class SyncProgressReport(ProgressReport):
    """
    Used to carry the state of the sync run as it proceeds. This object is used
    to update the on going progress in Pulp at appropriate intervals through
    the update_progress call. Once the sync is finished, this object should
    be used to produce the final report to return to Pulp to describe the
    sync.
    """

    # These states correspond to the progress of the manifest stage
    STATE_MANIFEST_IN_PROGRESS = 'manifest_in_progress'
    STATE_MANIFEST_FAILED = 'manifest_failed'
    # These states correspond to the progress of the file's stage. Note that
    # there is no STATE_MANIFEST_COMPLETE, as the next transition is
    # STATE_FILES_IN_PROGRESS
    STATE_FILES_IN_PROGRESS = 'files_in_progress'
    STATE_FILES_FAILED = 'files_failed'

    # A mapping of current states to allowed next states
    ALLOWED_STATE_TRANSITIONS = {
        ProgressReport.STATE_NOT_STARTED: (STATE_MANIFEST_IN_PROGRESS,
                                           ProgressReport.STATE_FAILED,
                                           ProgressReport.STATE_CANCELED),
        STATE_MANIFEST_IN_PROGRESS: (STATE_MANIFEST_FAILED,
                                     STATE_FILES_IN_PROGRESS,
                                     ProgressReport.STATE_CANCELED),
        STATE_FILES_IN_PROGRESS: (STATE_FILES_FAILED,
                                  ProgressReport.STATE_COMPLETE,
                                  ProgressReport.STATE_CANCELED)
    }

    def __init__(self, conduit=None, total_bytes=None, finished_bytes=0, num_files=None,
                 num_files_finished=0, files_error_messages=None, **kwargs):
        """
        Initialize the SyncProgressReport, setting all of the given parameters
        to it. See the superclass method of the same name for the use cases for the
        parameters.

        :param total_bytes:    The total number of bytes we need to download
        :type  total_bytes:    int
        :param finished_bytes: The number of bytes we have already downloaded
        :type  finished_bytes: int
        :param num_files:           The number of files that need to be
                                    downloaded or published
        :type  num_files:           int
        :param num_files_finished:  The number of files that have finished downloading
        :type  num_files_finished:  int
        :param files_error_messages: A dictionary mapping file names to
                                      errors encountered while downloading them
        :type  files_error_messages: dict
        :param conduit:  conduit
        :type  conduit:  RepoSyncConduit
        """
        super(self.__class__, self).__init__(conduit, **kwargs)

        # Let's also track how many bytes we've got on the files
        self.total_bytes = total_bytes
        self.finished_bytes = finished_bytes

        # These variables track the state of the file download stage
        self.num_files = num_files
        self.num_files_finished = num_files_finished
        # files_error_messages is a list of dictionaries with the keys 'name' and 'error'
        if files_error_messages is None:
            self.files_error_messages = []
        else:
            self.files_error_messages = files_error_messages

    def add_failed_file(self, file, error_report):
        """
        Updates the progress report that a file failed to be imported.

        :param file: The file object that failed to publish or download
        :type  file: file
        :param error_report: The error message that should be associated with the file
        :type  error_report: str
        """
        file_error = {'name': file.name, 'error': error_report}
        self.files_error_messages.append(file_error)

    def build_progress_report(self):
        """
        Returns the actual report that should be sent to Pulp as the current
        progress of the sync.

        :return: description of the current state of the sync
        :rtype:  dict
        """
        report = super(self.__class__, self).build_progress_report()

        report['total_bytes'] = self.total_bytes
        report['finished_bytes'] = self.finished_bytes
        report['num_files'] = self.num_files
        report['num_files_finished'] = self.num_files_finished
        report['files_error_messages'] = self.files_error_messages

        return report

    def _set_state(self, new_state):
        """
        This method allows users to set a new state to the ProgressReport.
        It enforces state transitions to only happen in a certain fashion.

        :param new_state: The new state that the caller wishes the ProgressReport to be set to
        :type  new_state: basestring
        """
        if new_state == self.STATE_COMPLETE and self.files_error_messages:
            new_state = self.STATE_FILES_FAILED

        if self._state == self.STATE_CANCELED:
            # Since STATE_CANCELED can be entered asynchonously during a repo sync, it is easier to
            # ignore other state transitions here than it is to find every place in our code where
            # we might attempt a state transition and check to see if we are cancelled. In sync.py,
            # all the download handlers (and the downloader itself) will do nothing if the state is
            # cancelled, so this is here to ensure that once we are cancelled, nothing can set the
            # state back to not cancelled.
            return

        super(self.__class__, self)._set_state(new_state)

    state = property(ProgressReport._get_state, _set_state)
