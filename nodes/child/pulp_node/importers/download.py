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
import tarfile

from logging import getLogger

from nectar.listener import AggregatingEventListener
from nectar.request import DownloadRequest

from pulp_node import constants
from pulp_node import pathlib
from pulp_node.error import UnitDownloadError


log = getLogger(__name__)


# --- constants --------------------------------------------------------------

STORAGE_PATH = constants.STORAGE_PATH
UNIT_REF = 'unit_ref'


# --- utils -------------------------------------------------------------------

def untar_dir(path, storage_path):
    """
    Replaces the tarball at the specified path with the extracted directory tree.
    :param path: The absolute path to a tarball.
    :type path: str
    :param storage_path: The path into which the content is extracted.
    :type storage_path: str
    :raise IOError: on i/o errors.
    """
    try:
        fp = tarfile.open(path)
        try:
            fp.extractall(path=storage_path)
        finally:
            fp.close()
    finally:
        if os.path.exists(path):
            os.unlink(path)


# --- downloading ------------------------------------------------------------

class UnitDownloadManager(AggregatingEventListener):
    """
    The content unit download manager.
    Listens for status changes to unit download requests and calls into the importer
    strategy object based on whether the download succeeded or failed.  If the download
    succeeded, the importer strategy is called to add the associated content unit (in the DB).
    In all cases, it checks the cancellation status of the sync request and when
    cancellation is detected, the downloader is cancelled.
    """

    @staticmethod
    def create_request(unit_URL, destination, unit, unit_ref):
        """
        Create a nectar download request compatible with the listener.
        The destination directory is created as needed.
        :param unit_URL: The download URL.
        :type unit_URL: str
        :param destination: The absolute path to where the file is to be downloaded.
        :type destination: str
        :param unit: A published content unit.
        :type unit: dict
        :param unit_ref: A reference to the unit association.
        :type unit_ref: pulp_node.manifest.UnitRef.
        :return: A nectar download request.
        :rtype: DownloadRequest
        """
        data = {
            STORAGE_PATH: unit[constants.STORAGE_PATH],
            UNIT_REF: unit_ref
        }
        dir_path = os.path.dirname(destination)
        pathlib.mkdir(dir_path)
        return DownloadRequest(unit_URL, destination, data=data)

    def __init__(self, strategy, request):
        """
        :param strategy: An importer strategy
        :type strategy: pulp_node.importer.strategy.ImporterStrategy.
        :param request: The nodes sync request.
        :type request: pulp_node.importers.strategies.SyncRequest.
        """
        super(self.__class__, self).__init__()
        self._strategy = strategy
        self.request = request

    def download_started(self, report):
        """
        A specific download (request) has started.
        Use this as an opportunity to handle cancellation.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport.
        """
        super(self.__class__, self).download_started(report)
        if self.request.cancelled():
            self.request.downloader.cancel()

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
        super(self.__class__, self).download_succeeded(report)
        storage_path = report.data[STORAGE_PATH]
        unit_ref = report.data[UNIT_REF]
        unit = unit_ref.fetch()
        unit[constants.STORAGE_PATH] = storage_path
        self._strategy.add_unit(self.request, unit)
        if unit.get(constants.TARBALL_PATH):
            untar_dir(report.destination, storage_path)
        if self.request.cancelled():
            self.request.downloader.cancel()

    def download_failed(self, report):
        """
        A specific download (request) has failed.
        Just need to check to see if the node sync request has been cancelled
        and cancel the downloader as needed.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport.:
        """
        super(self.__class__, self).download_failed(report)
        if self.request.cancelled():
            self.request.downloader.cancel()

    def error_list(self):
        """
        Return the aggregated list of errors.
        :return: The aggregated list of errors.
        :rtype: list
        """
        error_list = []
        for report in self.failed_reports:
            error = UnitDownloadError(report.url, self.request.repo_id, report.error_msg)
            error_list.append(error)
        return error_list
