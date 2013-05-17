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

from nectar.listener import AggregatingEventListener
from nectar.request import DownloadRequest
from pulp_node.error import UnitDownloadError


log = getLogger(__name__)


REQUEST = 'request'
UNIT_REF = 'unit_ref'


class DownloadListener(AggregatingEventListener):
    """
    The content unit download listener.
    """

    @staticmethod
    def create_request(url, request, storage_path, unit_ref):
        """
        Create a nectar download request compatible with the listener.
        :param url: The download URL.
        :type url: str
        :param request: The nodes sync request.
        :type request: pulp_node.importers.strategies.SyncRequest.
        :param storage_path: The absolute path to where the file is to be downloaded.
        :type storage_path: str
        :param unit_ref: A reference to the unit association.
        :type unit_ref: pulp_node.manifest.UnitDef.
        :return: A nectar download request.
        :rtype: DownloadRequest
        """
        return DownloadRequest(url, storage_path, data={REQUEST: request, UNIT_REF: unit_ref})

    def __init__(self, strategy):
        """
        :param strategy: An importer strategy
        :type strategy: pulp_node.importer.strategy.ImporterStrategy.
        """
        super(DownloadListener, self).__init__()
        self._strategy = strategy

    def download_started(self, report):
        """
        A specific download (request) has started.
          1. Check to see if the node sync request has been cancelled and cancel
             the downloader as needed.
          2. Create the destination directory structure as needed.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport.
        """
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
        """
        A specific download (request) has succeeded.
          1. Fetch the content unit using the reference.
          2. Update the storage_path on the unit.
          3. Add the unit.
          4. Check to see if the node sync request has been cancelled and cancel
             the downloader as needed.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport.
        """
        super(DownloadListener, self).download_succeeded(report)
        request = report.data[REQUEST]
        unit_ref = report.data[UNIT_REF]
        unit = unit_ref.fetch()
        unit['storage_path'] = report.destination
        self._strategy.add_unit(request, unit)
        if request.cancelled():
            request.downloader.cancel()

    def download_failed(self, report):
        """
        A specific download (request) has failed.
        Just need to check to see if the node sync request has been cancelled
        and cancel the downloader as needed.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport.:
        """
        super(DownloadListener, self).download_failed(report)
        request = report.data[REQUEST]
        if request.cancelled():
            request.downloader.cancel()

    def error_list(self):
        """
        Return the aggregated list of errors.
        :return: The aggregated list of errors.
        :rtype: list
        """
        error_list = []
        for report in self.failed_reports:
            request = report.data[REQUEST]
            error = UnitDownloadError(report.url, request.repo_id, report.error_report)
            error_list.append(error)
        return error_list
