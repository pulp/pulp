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


from pulp_citrus.transport import DownloadTracker, DownloadRequest


class Tracker(DownloadTracker):
    """
    The unit download tracker (listener).
    :ivar _strategy: A strategy object.
    :type _strategy: Strategy
    :ivar _failed: The list of units that failed to be downloaded and the
        exception raised during the download.
    :type _failed: list
    """

    def __init__(self, strategy):
        """
        :param repository: The strategy object.
        :type repository: Strategy
        """
        self._strategy = strategy
        self._failed = []

    def succeeded(self, request):
        """
        Called when a download request succeeds.
        Add to succeeded list and notify the strategy.
        :param request: The download request that succeeded.
        :type request: DownloadRequest
        """
        unit = request.local_unit
        try:
            self._strategy.add_unit(unit)
        except Exception, e:
            self._failed.append((unit, e))

    def failed(self, request, exception):
        """
        Called when a download request fails.
        Add to the failed list.
        :param request: The download request that failed.
        :type request: DownloadRequest
        """
        unit = request.local_unit
        self._failed.append((unit, exception))

    def get_failed(self):
        """
        Get a list of units that failed to download.
          Each item is: (unit, exception)
        :return: List of units that failed to download.
        """
        return self._failed