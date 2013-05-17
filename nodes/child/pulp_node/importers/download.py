# Copyright (c) 2013 Red Hat, Inc.
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
import errno

from logging import getLogger

from pulp.common.download.listener import AggregatingEventListener
from pulp.common.download.request import DownloadRequest
from pulp_node.error import UnitDownloadError


log = getLogger(__name__)


REQUEST = 'request'
UNIT_REF = 'unit_ref'


class UnitDownloadRequest(DownloadRequest):

    def __init__(self, url, request, storage_path, ref):
        super(UnitDownloadRequest, self).__init__(
            url, storage_path, data={REQUEST: request, UNIT_REF: ref})


class DownloadListener(AggregatingEventListener):

    def __init__(self, strategy):
        super(DownloadListener, self).__init__()
        self._strategy = strategy

    def download_started(self, report):
        super(DownloadListener, self).download_started(report)
        request = report.data[REQUEST]
        if request.cancelled():
            request.downloader.cancel()
            return
        try:
            dir_path = os.path.dirname(report.destination)
            os.makedirs(dir_path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise e

    def download_succeeded(self, report):
        super(DownloadListener, self).download_succeeded(report)
        request = report.data[REQUEST]
        unit_ref = report.data[UNIT_REF]
        unit = unit_ref.fetch()
        unit['storage_path'] = report.destination
        self._strategy.add_unit(request, unit)
        if request.cancelled():
            request.downloader.cancel()

    def download_failed(self, report):
        super(DownloadListener, self).download_failed(report)
        request = report.data[REQUEST]
        if request.cancelled():
            request.downloader.cancel()

    def error_list(self):
        error_list = []
        for report in self.failed_reports:
            request = report.data[REQUEST]
            error = UnitDownloadError(report.url, request.repo_id, report.error_report)
            error_list.append(error)
        return error_list