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

from eventlet import GreenPool
from eventlet.green import urllib2

from pulp.common.download import report as download_report
from pulp.common.download.backends.base import DownloadBackend


DEFAULT_MAX_CONCURRENT = 20


class HTTPEventletDownloadBackend(DownloadBackend):

    @property
    def max_concurrent(self):
        return self.config.max_concurrent or DEFAULT_MAX_CONCURRENT

    def download(self, request_list):

        def _fetch(request):
            file_handle = request.destination

            if isinstance(request.destination, basestring):
                file_handle = open(request.destination, 'wb')

            body = urllib2.urlopen(request.url).read()

            file_handle.write(body)

            if file_handle is not request.destination:
                file_handle.close()

            return request

        report_dict = dict((request, download_report.DownloadReport.from_download_request(request))
                           for request in request_list)

        pool = GreenPool(size=self.max_concurrent)

        for request in pool.imap(_fetch, request_list):
            pass

        return report_dict.values()

