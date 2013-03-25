# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from datetime import datetime

from pulp.common import dateutils

# download states --------------------------------------------------------------

DOWNLOAD_WAITING = 'waiting'
DOWNLOAD_DOWNLOADING = 'downloading'
DOWNLOAD_SUCCEEDED = 'succeeded'
DOWNLOAD_FAILED = 'failed'
DOWNLOAD_CANCELED = 'canceled'

# download report --------------------------------------------------------------

class DownloadReport(object):
    """
    Report object for individual downloads.

    :ivar url:              url requested to be downloaded
    :ivar destination:      destination of the downloaded file, either a string representing the
                            filesystem path to the file, or a file-like object
    :ivar state:            current state of the download (waiting, downloading, succeeded, failed,
                            canceled)
    :ivar total_bytes:      total bytes of the file to be downloaded, None if this could not be
                            determined
    :ivar bytes_downloaded: bytes of the file downloaded so far
    :ivar start_time:       start time of the file download
    :ivar finish_time:      finish time of the file download
    :ivar error_report:     arbitrary dictionary containing debugging info in the event of a
                            failure
    """

    @classmethod
    def from_download_request(cls, request):
        """
        Factory method for building a report based on a request
        :param request: request to build a report for
        :type request: pulp.common.download.request.DownloadRequest
        :return: report for request
        :rtype: pulp.common.download.report.DownloadReport
        """
        return cls(request.url, request.destination, request.data)

    def __init__(self, url, destination, data=None):
        """
        :param url:         url requested to be downloaded
        :type  url:         str
        :param destination: destination of the downloaded file, either a string representing the
                            filesystem path to the file, or a file-like object
        :type  destination: str or file-like object
        :param data:        arbitrary data attached to the request instance
        """

        self.url = url
        self.destination = destination
        self.data = data

        self.state = DOWNLOAD_WAITING
        self.total_bytes = None
        self.bytes_downloaded = 0
        self.start_time = None
        self.finish_time = None
        self.error_report = {}

    # state management methods -------------------------------------------------

    def download_started(self):
        """
        Mark the report as having started.

        This method is "re-entrant" in the sense that it is only changes the
        report's state the first time it is called. Subsequent calls amount to
        no-ops.
        """
        if self.state is not DOWNLOAD_WAITING:
            return
        self.state = DOWNLOAD_DOWNLOADING
        self.start_time = datetime.now(tz=dateutils.utc_tz())

    def download_succeeded(self):
        """
        Mark the report as having succeeded.

        This method is "re-entrant" in the sense that it is only changes the
        report's state the first time it is called. Subsequent calls to this
        method or download_failed or download_canceled amount to no-ops.
        """
        self._download_finished(DOWNLOAD_SUCCEEDED)

    def download_failed(self):
        """
        Mark the report as having failed.

        This method is "re-entrant" in the sense that it is only changes the
        report's state the first time it is called. Subsequent calls to this
        method or download_succeeded or download_canceled amount to no-ops.
        """
        self._download_finished(DOWNLOAD_FAILED)

    def download_canceled(self):
        """
        Mark the report as having been canceled.

        This method is "re-entrant" in the sense that it is only changes the
        report's state the first time it is called. Subsequent calls to this
        method or download_succeeded or download_failed amount to no-ops.
        """
        self._download_finished(DOWNLOAD_CANCELED)

    def _download_finished(self, state):
        if self.state is not DOWNLOAD_DOWNLOADING:
            return
        self.state = state
        self.finish_time = datetime.now(tz=dateutils.utc_tz())

