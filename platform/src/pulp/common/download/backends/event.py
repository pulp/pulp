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

from collections import defaultdict
from datetime import datetime
from logging import getLogger

from eventlet import GreenPool
from eventlet.green import urllib2

from pulp.common.download import report as download_report
from pulp.common.download.backends.base import DownloadBackend


# taken from python documentation <http://docs.python.org/2.6/library/socket.html#socket.socket.recv>
DEFAULT_BUFFER_SIZE = 4096

# based on empirical observation
DEFAULT_MAX_CONCURRENT = 100

_LOG = getLogger(__name__)

# eventlet downloader backend --------------------------------------------------

class HTTPEventletDownloadBackend(DownloadBackend):

    @property
    def buffer_size(self):
        return self.config.buffer_size or DEFAULT_BUFFER_SIZE

    @property
    def max_concurrent(self):
        return self.config.max_concurrent or DEFAULT_MAX_CONCURRENT

    def download(self, request_list):

        # fetch closure --------------------------------------------------------

        def _fetch(request):
            # get the appropriate report
            report = report_dict[request]

            # once we're canceled, short-circuit these calls as there's no way
            # to interrupt the imap call
            if self.is_cancelled:
                report.state = download_report.DOWNLOAD_CANCELED
                return report

            # and set the corresponding information for it
            report.state = download_report.DOWNLOAD_DOWNLOADING
            report.start_time = datetime.utcnow()
            self.fire_download_started(report)

            # setup the destination file handle
            file_handle = request.destination
            if isinstance(request.destination, basestring):
                file_handle = open(request.destination, 'wb')

            # make the request to the server and process the response
            try:
                urllib2_request = download_request_to_urllib2_request(self.config, request)
                response = urllib2.urlopen(urllib2_request)
                info = response.info()
                set_response_info(info, report)

                # individual file download i/o loop
                while not self.is_cancelled:
                    body = response.read(self.buffer_size)
                    if not body:
                        break

                    file_handle.write(body)

                    bytes = len(body)
                    report.bytes_downloaded += bytes
                    self.fire_download_progress(report)

                else:
                    # the only way we don't break out of the i/o loop, is if
                    # we were canceled
                    report.state = download_report.DOWNLOAD_CANCELED

            except Exception, e:
                report.state = download_report.DOWNLOAD_FAILED
                _LOG.exception(e)

            else:
                # don't overwrite the state if we were canceled
                if report.state is download_report.DOWNLOAD_DOWNLOADING:
                    report.state = download_report.DOWNLOAD_SUCCEEDED

            finally:
                report.finish_time = datetime.utcnow()
                # close the file handle if we opened it
                if file_handle is not request.destination:
                    file_handle.close()

            # return the appropriately filled out report
            return report

        # download implementation ----------------------------------------------

        # XXX (jconnor 2013-03-06) is this going to blow our benefits from using
        # generators as the request list?
        report_dict = dict((request, download_report.DownloadReport.from_download_request(request))
                           for request in request_list)
        # it would be much cooler to have a "lazy" default dict, where the lazy
        # instantiates the report from the request key on demand
        #report_dict = defaultdict(download_report.DownloadReport.from_download_request).fromkeys(request_list)

        self.fire_batch_started(report_dict.itervalues())

        pool = GreenPool(size=self.max_concurrent)

        # main i/o loop
        for report in pool.imap(_fetch, request_list):
            # event callbacks called here to keep them from gumming up the
            # concurrent fetch calls
            if report.state is download_report.DOWNLOAD_SUCCEEDED:
                self.fire_download_succeeded(report)
            else:
                self.fire_download_failed(report)

        self.fire_batch_finished(report_dict.itervalues())

        return report_dict.values()

# utilities --------------------------------------------------------------------

def download_request_to_urllib2_request(config, download_request):
    urllib2_request = urllib2.Request(download_request.url)
    # TODO (jconnor 2013-02-06) add ssl support
    # TODO (jconnor 2013-02-06) add proxy support
    # TODO (jconnor 2013-02-06) add throttling support, if possible
    return urllib2_request


def set_response_info(info, report):
    # XXX (jconnor 2013-02-06) is there anything else we need?
    content_length = info.dict.get('content-length', 0)
    report.total_bytes = int(content_length)


