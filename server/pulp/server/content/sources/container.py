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
from pulp.server.content.sources.model import ContentSource, PrimarySource, RefreshReport


log = getLogger(__name__)


class ContentContainer(object):
    """
    The content container represents a virtual collection of content that is
    supplied by a collection of content sources.
    :ivar sources: A dictionary of content sources keyed by source ID.
    :type sources: dict
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

    def __init__(self, path=None):
        """
        :param path: The absolute path to a directory containing
            content source descriptor files.
        :type path: str
        """
        self.sources = ContentSource.load_all(path)

    def download(self, cancel_event, downloader, request_list, listener=None):
        """
        Download files using available alternate content sources.
        An attempt is made to satisfy each download request using the alternate
        content sources in the order specified by priority.  The specified
        downloader is designated as the primary source and is used in the event that
        the request cannot be completed using alternate sources.
        :param cancel_event: An event that indicates the download has been canceled.
        :type cancel_event: threading.Event
        :param downloader: A primary nectar downloader.  Used to download the
            requested content unit when it cannot be achieved using alternate
            content sources.
        :type downloader: nectar.downloaders.base.Downloader
        :param request_list: A list of pulp.server.content.sources.model.Request.
        :type request_list: list
        :param listener: An optional download request listener.
        :type listener: Listener
        """
        self.refresh(cancel_event)
        primary = PrimarySource(downloader)
        for request in request_list:
            request.find_sources(primary, self.sources)
        while not cancel_event.isSet():
            collated = self.collated(request_list)
            if not collated:
                #  Either we have exhausted our content sources or all
                #  of the requests have been satisfied.
                break
            for source, nectar_list in collated.items():
                downloader = source.downloader()
                downloader.event_listener = NectarListener(cancel_event, downloader, listener)
                downloader.download(nectar_list)
                if cancel_event.isSet():
                    break

    def refresh(self, cancel_event, force=False):
        """
        Refresh the content catalog using available content sources.
        :param cancel_event: An event that indicates the refresh has been canceled.
        :type cancel_event: threading.Event
        :param force: Force refresh of content sources with unexpired catalog entries.
        :type force: bool
        :return: A list of refresh reports.
        :rtype: list of: pulp.server.content.sources.model.RefreshReport
        """
        reports = []
        catalog = managers.content_catalog_manager()
        for source_id, source in self.sources.items():
            if cancel_event.isSet():
                break
            if force or not catalog.has_entries(source_id):
                try:
                    report = source.refresh(cancel_event)
                    reports.extend(report)
                except Exception, e:
                    log.error('refresh %s, failed: %s', source_id, e)
                    report = RefreshReport(source_id, '')
                    report.errors.append(str(e))
                    reports.append(report)
        catalog.purge_expired()
        return reports

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
    Download event listener.
    """

    def download_started(self, request):
        """
        Notification that downloading has started for the specified request.
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """

    def download_succeeded(self, request):
        """
        Notification that downloading has succeeded for the specified request.
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """

    def download_failed(self, request):
        """
        Notification that downloading has failed for the specified request.
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request
        """


class NectarListener(DownloadEventListener):

    @staticmethod
    def _notify(method, request):
        """
        Safely invoke the method forwarding a notification to the listener.
        Catch and log exceptions.
        :param method: A listener method.
        :type method: callable
        :param request: A download request.
        :type request: pulp.server.content.sources.model.Request.
        """
        try:
            method(request)
        except Exception:
            log.exception(str(method))

    def __init__(self, cancel_event, downloader, listener=None):
        """
        :param cancel_event: An event that indicates the download has been canceled.
        :type cancel_event: threading.Event
        :param downloader: The active nectar downloader.
        :type downloader: nectar.downloaders.base.Downloader
        :param listener: An optional download request listener.
        :type listener: Listener
        """
        self.cancel_event = cancel_event
        self.downloader = downloader
        self.listener = listener

    def download_started(self, report):
        """
        Nectar download started.
        Forwarded to the listener registered with the container.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport
        """
        if self.cancel_event.isSet():
            self.downloader.cancel()
            return
        request = report.data
        listener = self.listener
        if not listener:
            return
        self._notify(listener.download_started, request)

    def download_succeeded(self, report):
        """
        Nectar download succeeded.
        The associated request is marked as succeeded.
        Forwarded to the listener registered with the container.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport
        """
        if self.cancel_event.isSet():
            self.downloader.cancel()
            return
        request = report.data
        request.downloaded = True
        listener = self.listener
        if not listener:
            return
        self._notify(listener.download_succeeded, request)

    def download_failed(self, report):
        """
        Nectar download failed.
        Forwarded to the listener registered with the container.
        The request is marked as failed ONLY if the request has no more
        content sources to try.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport
        """
        if self.cancel_event.isSet():
            self.downloader.cancel()
            return
        request = report.data
        request.errors.append(report.error_msg)
        listener = self.listener
        if not listener:
            return
        if request.has_source():
            return
        self._notify(listener.download_failed, request)
