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

"""
Generic transport classes.
"""

from logging import getLogger


log = getLogger(__name__)


class Transport:
    """
    The transport interface.
    """

    def download(self, requests):
        """
        Process the specified download requests.
        @param requests: A list of L{DownloadRequest} objects.
        @type requests: list
        """
        pass

    def cancel(self):
        """
        Cancel an active download.
        """
        pass


class DownloadTracker:
    """
    Track progress of download requests.
    """

    def succeeded(self, request):
        """
        Called when a download request succeeds.
        @param request: The download request that succeeded.
        @type request: L{DownloadRequest}
        """
        pass

    def failed(self, request, exception):
        """
        Called when a download request fails.
        @param request: The download request that failed.
        @type request: L{DownloadRequest}
        """
        pass


class DownloadRequest:
    """
    The download request provides integration between the importer
    and the transport layer.  It's used to request the download of
    the file referenced by a content unit.
    @ivar importer: The importer making the request.
    @type importer: L{Importer}
    @ivar unit: The upstream content unit.
    @type unit: dict
    @ivar local_unit: A local content unit that is in the process of
        being added.  The request is to download the file referenced
        in the unit.
    @type local_unit: L{Unit}
    """

    def __init__(self, tracker, unit, local_unit):
        """
        @param tracker: A download tracker.
        @type tracker: L{DownloadTracker}
        @param unit: The upstream content unit.
        @type unit: dict
        @param local_unit: A local content unit that is in the process of
            being added.  The request is to download the file referenced
            in the unit.
        @type local_unit: L{Unit}
        """
        self.tracker = tracker
        self.unit = unit
        self.local_unit = local_unit

    def details(self):
        """
        Get the details specified by the upstream unit to be used for
        the download.  A value of 'None' indicates that there is no file
        to be downloaded.  Contains information such as URL for http transports.
        @return: The download specification.
        @rtype: dict
        """
        return self.unit.get('_download')

    def succeeded(self):
        """
        Called by the transport to indicate the requested download succeeded.
        """
        self.tracker.succeeded(self)

    def failed(self, exception):
        """
        Called by the transport to indicate the requested download failed.
        @param exception: The exception raised.
        @type exception: Exception
        """
        self.tracker.failed(self, exception)