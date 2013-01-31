# Copyright (c) 2012 Red Hat, Inc.
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

from pulp.common.download.listener import DownloadEventListener
from pulp.common.download.request import DownloadRequest

log = getLogger(__name__)


class Batch:
    """
    A collection of download requests and a mapping of unit by URL.
    :ivar units: A mapping of units by URL.
    :type units: dict
    :ivar request_list: A list of download requests
    :type request_list: list
    """

    def __init__(self):
        self.units = {}
        self.request_list = []

    def add(self, url, unit):
        """
        Add a unit to the download batch.
        :param url: The download URL.
        :type url: str
        :param unit: A content unit.
        :type unit: pulp.plugins.model.Unit
        """
        self.units[url] = unit
        request = DownloadRequest(str(url), unit.storage_path)
        self.request_list.append(request)


class DownloadListener(DownloadEventListener):

    def __init__(self, strategy, batch):
        self.strategy = strategy
        self.batch = batch
        self.failed = []

    @property
    def progress(self):
        return self.strategy.progress

    def download_started(self, report):
        try:
            dir_path = os.path.dirname(report.file_path)
            os.makedirs(dir_path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise e

    def download_succeeded(self, report):
        self.progress.set_action('downloaded', report.url)
        unit = self.batch.units.get(report.url)
        try:
            self.strategy.add_unit(unit)
        except Exception, e:
            log.exception(report.url)
            self.failed.append((unit, e))

    def download_failed(self, report):
        unit = self.batch.units[report.url]
        self.failed.append((unit, report.error_report))
