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
from pulp.common.download.backends.base import DownloadBackend


DEFAULT_MAX_CONCURRENT = 20

_LOG = getLogger(__name__)


class HTTPEventletDownloadBackend(DownloadBackend):

    @property
    def max_concurrent(self):
        return self.config.max_concurrent or DEFAULT_MAX_CONCURRENT

    def download(self, request_list):

        # fetch closure --------------------------------------------------------

        def _fetch(request):
            report = report_dict[request]
            report.state = download_report.DOWNLOAD_DOWNLOADING
            self.fire_download_started(report)

            file_handle = request.destination

            if isinstance(request.destination, basestring):
                file_handle = open(request.destination, 'wb')

            try:
                body = urllib2.urlopen(request.url).read()
                file_handle.write(body)

                # XXX (jconnor 2013-03-06) need to find a more fine-grained way
                # to do downloading and progress reporting
                bytes = len(body)
                report.bytes_downloaded = bytes
                self.fire_download_progress(report)

                if file_handle is not request.destination:
                    file_handle.close()

            except Exception, e:
                report.state = download_report.DOWNLOAD_FAILED
                _LOG.exception(e)

            else:
                report.state = download_report.DOWNLOAD_SUCCEEDED

            return report

        # download implementation ----------------------------------------------

        report_dict = dict((request, download_report.DownloadReport.from_download_request(request))
                           for request in request_list)

        self.fire_batch_started(report_dict.itervalues())

        pool = GreenPool(size=self.max_concurrent)

        for report in pool.imap(_fetch, request_list):
            if report.state is download_report.DOWNLOAD_SUCCEEDED:
                self.fire_download_succeeded(report)
            else:
                self.fire_download_failed(report)

        self.fire_batch_finished(report_dict.itervalues())

        return report_dict.values()

