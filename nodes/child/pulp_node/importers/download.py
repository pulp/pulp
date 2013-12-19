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

from pulp.server.content.sources import Listener, Request

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

class ContentDownloadListener(Listener):
    """
    The content unit download event listener.
    Listens for status changes to unit download requests and calls into the importer
    strategy object based on whether the download succeeded or failed.  If the download
    succeeded, the importer strategy is called to add the associated content unit (in the DB).
    """

    @staticmethod
    def create_request(url, destination, unit, unit_ref):
        """
        Create a content container download request that is compatible with the listener.
        The destination directory is created as needed.
        :param url: The download URL.
        :type url: str
        :param destination: The absolute path to where the file is to be downloaded.
        :type destination: str
        :param unit: A published content unit.
        :type unit: dict
        :param unit_ref: A reference to the unit association.
        :type unit_ref: pulp_node.manifest.UnitRef.
        :return: A download request.
        :rtype: Request
        """
        data = {
            STORAGE_PATH: unit[constants.STORAGE_PATH],
            UNIT_REF: unit_ref
        }
        dir_path = os.path.dirname(destination)
        pathlib.mkdir(dir_path)
        request = Request(unit[constants.TYPE_ID], unit[constants.UNIT_KEY], url, destination)
        request.data = data
        return request

    def __init__(self, strategy, request):
        """
        :param strategy: An importer strategy object.
        :type strategy: pulp_node.importer.strategy.ImporterStrategy.
        :param request: The nodes synchronization request.
        :type request: pulp_node.importers.strategies.SyncRequest.
        """
        super(self.__class__, self).__init__()
        self._strategy = strategy
        self.request = request
        self.error_list = []

    def download_succeeded(self, request):
        """
        A specific download (request) has succeeded.
          1. Fetch the content unit using the reference.
          2. Update the storage_path on the unit.
          3. Add the unit.
          4. Extract downloaded tarballs as needed.
        :param request: The download request that succeeded.
        :type request: Request
        """
        storage_path = request.data[STORAGE_PATH]
        unit_ref = request.data[UNIT_REF]
        unit = unit_ref.fetch()
        unit[constants.STORAGE_PATH] = storage_path
        self._strategy.add_unit(self.request, unit)
        if unit.get(constants.TARBALL_PATH):
            untar_dir(request.destination, storage_path)

    def download_failed(self, request):
        """
        A specific download (request) has failed.
        Append download request errors to our list of errors.
        :param request: The download request that failed.
        :type request: Request
        """
        for msg in request.errors:
            error = UnitDownloadError(request.url, self.request.repo_id, msg)
            self.error_list.append(error)
