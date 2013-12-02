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

from logging import getLogger

from nectar.listener import DownloadEventListener
from nectar.request import DownloadRequest

from pulp.server.managers import factory as managers
from pulp.server.content.sources.model import ContentSource, PrimarySource


log = getLogger(__name__)


class Coordinator(object):
    """
    Coordinate content source operations such as refreshing the catalog
    and downloading files associated with content units.
    :ivar sources: A dictionary of content sources keyed by source ID.
    :type sources: dict
    :ivar listener: An optional download request listener.
    :type listener: Listener
    :ivar cancelled: Request cancelled flag.
    :type cancelled: bool
    """

    @staticmethod
    def collated(request_list):
        """
        Get a dictionary of nectar download requests collated
        (keyed) by content source.
        :param request_list: A list of pulp.server.content.sources.model.Request.
        :type request_list: list
        :return: A dictionary of nectar download requests
            collated by content source.
        :rtype: dict
        """
        collated = {}
        for request in request_list:
            if request.downloaded:
                continue
            source = request.next_source()
            if source is None:
                continue
            nectar_list = collated.setdefault(source[0], [])
            nectar_request = DownloadRequest(source[1], request.destination, data=request)
            nectar_list.append(nectar_request)
        return collated

    def __init__(self, path=None, listener=None):
        """
        :param path: The absolute path to a directory containing
            content source descriptor files.
        :type path: str
        :param listener: An optional download request listener.
        :type listener: Listener
        """
        self.sources = ContentSource.load_all(path)
        self.listener = listener
        self.cancelled = False

    def cancel(self):
        """
        Cancel the current operation.
        """
        self.cancelled = True

    def download(self, downloader, request_list):
        """
        Download files using available alternate content sources.
        An attempt is made to satisfy each download request using alternate
        content sources in the order specified by priority.  The specified
        downlaoder is used when alternate sources are exhausted.
        :param downloader: A primary nectar downloader.  Used to download the
            requested content unit when it cannot be achieved using alternate
            content sources.
        :param request_list: A list of pulp.server.content.sources.model.Request.
        :type request_list: list
        """
        self.cancelled = False
        self.refresh()
        primary = PrimarySource(downloader)
        for request in request_list:
            request.find_sources(primary, self.sources)
        while not self.cancelled:
            collated = self.collated(request_list)
            if not collated:
                break
            for source, nectar_list in collated.items():
                if not nectar_list:
                    continue
                downloader = source.downloader()
                downloader.event_listener = _Listener(self, downloader)
                downloader.download(nectar_list)

    def refresh(self, force=False):
        """
        Refresh the content catalog using available content sources.
        :param force: Force refresh of content sources with unexpired catalog entries.
        :type force: bool
        """
        catalog = managers.content_catalog_manager()
        for source_id, source in self.sources.items():
            if self.cancelled:
                return
            if force or not catalog.has_entries(source_id):
                try:
                    source.refresh()
                except Exception, e:
                    log.error('refresh %s, failed: %s', source_id, e)
        catalog.purge_expired()

    def purge_orphans(self):
        """
        Purge the catalog of orphaned entries.
        Orphans are entries are those entries contributed by a content
        source that no longer exists.
        """
        valid_ids = list(self.sources.keys())
        catalog = managers.content_catalog_manager()
        catalog.purge_orphans(valid_ids)


class Listener(object):
    """
    A download event listener.
    """

    def download_started(self, request):
        """
        Notification that the downloading has started for the specified request.
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """

    def download_succeeded(self, request):
        """
        Notification that the downloading has succeeded for the specified request.
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """

    def download_failed(self, request):
        """
        Notification that the downloading has failed for the specified request.
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """


# --- nectar -----------------------------------------------------------------


class _Listener(DownloadEventListener):

    @staticmethod
    def _notify(method, request):
        try:
            method(request)
        except Exception:
            log.exception(request.id)

    def __init__(self, coordinator, downloader):
        self.coordinator = coordinator
        self.downloader = downloader

    def download_started(self, report):
        if self.coordinator.cancelled:
            self.downloader.cancel()
            return
        request = report.data
        listener = self.coordinator.listener
        if not listener:
            return
        self._notify(listener.download_started, request)

    def download_succeeded(self, report):
        if self.coordinator.cancelled:
            self.downloader.cancel()
            return
        request = report.data
        request.downloaded = True
        listener = self.coordinator.listener
        if not listener:
            return
        self._notify(listener.download_succeeded, request)

    def download_failed(self, report):
        if self.coordinator.cancelled:
            self.downloader.cancel()
            return
        request = report.data
        request.errors.append(report.error_msg)
        listener = self.coordinator.listener
        if not listener:
            return
        if request.has_source():
            return
        self._notify(listener.download_failed, request)
