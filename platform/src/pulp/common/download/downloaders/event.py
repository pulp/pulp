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

from logging import getLogger

from eventlet import GreenPool
from eventlet.green import urllib2

from pulp.common.download import report as download_report
from pulp.common.download.downloaders.base import PulpDownloader


# "optimal" concurrency, based purely on anecdotal evidence
DEFAULT_MAX_CONCURRENT = 7

# taken from python's socket._fileobject wrapper
DEFAULT_BUFFER_SIZE = 8192
NO_RETURN_BUFFER_SIZE = -1

DEFAULT_MAX_PROGRESS_CALLS = 10

_LOG = getLogger(__name__)

# eventlet downloader ----------------------------------------------------------

class HTTPEventletDownloader(PulpDownloader):
    """
    Backend that is optimized for downloading large quantities of files.

    This backend does *not* support the event listener batch callbacks.
    Its download method also returns None instead of a list of reports.
    Both of these deviations keep the backend itself from adding the memory
    overhead.
    """

    @property
    def max_concurrent(self):
        return self.config.max_concurrent or DEFAULT_MAX_CONCURRENT

    def download(self, request_list):

        pool = GreenPool(size=self.max_concurrent)

        # main i/o loop
        for report in pool.imap(self._fetch, request_list):
            # event callbacks called here to keep them from gumming up the
            # concurrent fetch calls
            if report.state is download_report.DOWNLOAD_SUCCEEDED:
                self.fire_download_succeeded(report)
            else:
                self.fire_download_failed(report)

    def _fetch(self, request):
        report = download_report.DownloadReport.from_download_request(request)
        report.download_started()

        # once we're canceled, short-circuit these calls as there's no way
        # to interrupt the imap call's iterations
        if self.is_canceled:
            report.download_canceled()
            return report

        self.fire_download_started(report)

        file_handle = request.initialize_file_handle()
        buffer_size = calculate_buffer_size(report, DEFAULT_MAX_PROGRESS_CALLS-1)

        # make the request to the server and process the response
        try:
            urllib2_request = download_request_to_urllib2_request(self.config, request)
            response = urllib2.urlopen(urllib2_request)
            info = response.info()
            set_response_info(info, report)

            self.fire_download_progress(report) # fire an initial progress event

            # individual file download i/o loop
            while not self.is_canceled:
                body = response.read(buffer_size)
                if not body:
                    break

                file_handle.write(body)

                bytes_read = len(body)
                report.bytes_downloaded += bytes_read
                # this is guaranteed to fire at least one (final) progress event
                self.fire_download_progress(report)

            else:
                # we didn't break out of the i/o loop only if we were cancelled
                report.download_canceled()

        except Exception, e:
            report.download_failed()
            _LOG.exception(e)

        else:
            report.download_succeeded()

        finally:
            request.finalize_file_handle()

        # return the appropriately filled out report
        return report

# utilities --------------------------------------------------------------------

def calculate_buffer_size(report, max_progress_calls=DEFAULT_MAX_PROGRESS_CALLS):
    # if we've been unable to determine the size of the download, return a
    # buffer size that won't bother with reporting the progress
    if not report.total_bytes or report.total_bytes < 1:
        return NO_RETURN_BUFFER_SIZE

    # return a buffer size that allows for a maximum number of progress calls,
    # but don't bother returning a buffer size smaller than the default;
    # the read() operation won't honor it anyway

    divisor = max_progress_calls
    if report.total_bytes % divisor != 0:
        divisor -= 1

    potential_buffer_size = report.total_bytes / divisor
    buffer_size = max(potential_buffer_size, DEFAULT_BUFFER_SIZE)
    return buffer_size


def download_request_to_urllib2_request(config, download_request):
    urllib2_request = urllib2.Request(download_request.url)
    # TODO (jconnor 2013-02-06) add ssl support
    # TODO (jconnor 2013-02-06) add proxy support
    # TODO (jconnor 2013-02-06) add throttling support, if possible
    return urllib2_request


def set_response_info(info, report):
    # XXX (jconnor 2013-02-06) is there anything else we need?
    content_length = info.dict.get('content-length', None)
    if content_length is not None:
        report.total_bytes = int(content_length)


