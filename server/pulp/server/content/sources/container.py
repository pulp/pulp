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

from time import sleep
from Queue import Queue, Empty, Full
from threading import Thread, RLock
from collections import namedtuple
from logging import getLogger

from nectar.listener import DownloadEventListener
from nectar.request import DownloadRequest
from nectar.report import DownloadReport as NectarDownloadReport

from pulp.server.managers import factory as managers
from pulp.server.content.sources.model import ContentSource, PrimarySource, \
    DownloadReport, DownloadDetails, RefreshReport


log = getLogger(__name__)


class ContentContainer(object):
    """
    The content container represents a virtual collection of content that is
    supplied by a collection of content sources.
    :ivar sources: A dictionary of content sources keyed by source ID.
    :type sources: dict
    """

    def __init__(self, path=None):
        """
        :param path: The absolute path to a directory containing
            content source descriptor files.
        :type path: str
        """
        self.sources = ContentSource.load_all(path)

    def download(self, canceled, downloader, requests, listener=None):
        """
        Download files using available alternate content sources.
        An attempt is made to satisfy each download request using the alternate
        content sources in the order specified by priority.  The specified
        downloader is designated as the primary source and is used in the event that
        the request cannot be completed using alternate sources.
        :param canceled: An event that indicates the download has been canceled.
        :type canceled: threading.Event
        :param downloader: A primary nectar downloader.  Used to download the
            requested content unit when it cannot be achieved using alternate content sources.
        :type downloader: nectar.downloaders.base.Downloader
        :param requests: An iterable of pulp.server.content.sources.model.Request.
        :type requests: iterable
        :param listener: An optional download request listener.
        :type listener: Listener
        :return: A download report.
        :rtype: DownloadReport
        """
        self.refresh(canceled)
        primary = PrimarySource(downloader)
        batch = Batch(canceled, primary, self.sources, requests, listener)
        report = batch.download()
        return report

    def refresh(self, canceled, force=False):
        """
        Refresh the content catalog using available content sources.
        :param canceled: An event that indicates the refresh has been canceled.
        :type canceled: threading.Event
        :param force: Force refresh of content sources with unexpired catalog entries.
        :type force: bool
        :return: A list of refresh reports.
        :rtype: list of: pulp.server.content.sources.model.RefreshReport
        """
        reports = []
        catalog = managers.content_catalog_manager()
        for source_id, source in self.sources.items():
            if canceled.isSet():
                break
            if force or not catalog.has_entries(source_id):
                try:
                    report = source.refresh(canceled)
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
    def _forward(method, request):
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

    def __init__(self, batch):
        """
        :param batch: A download batch.
        :type batch: Batch
        """
        self.batch = batch
        self.total_succeeded = 0
        self.total_failed = 0

    def download_started(self, report):
        """
        Nectar download started.
        Forwarded to the listener registered with the container.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport
        """
        if self.batch.is_canceled:
            # canceled
            return
        request = report.data
        listener = self.batch.listener
        if not listener:
            # nobody listening
            return
        self._forward(listener.download_started, request)

    def download_succeeded(self, report):
        """
        Nectar download succeeded.
        The associated request is marked as succeeded.
        Forwarded to the listener registered with the container.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport
        """
        self.total_succeeded += 1
        if self.batch.is_canceled:
            # canceled
            return
        request = report.data
        request.downloaded = True
        listener = self.batch.listener
        self.batch.finished(request)
        if not listener:
            # nobody listening
            return
        self._forward(listener.download_succeeded, request)

    def download_failed(self, report):
        """
        Nectar download failed.
        Forwarded to the listener registered with the container.
        The request is marked as failed ONLY if the request has no more
        content sources to try.
        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport
        """
        self.total_failed += 1
        if self.batch.is_canceled:
            # canceled
            return
        request = report.data
        request.errors.append(report.error_msg)
        listener = self.batch.listener
        if self.batch.dispatch(request):
            # trying another
            return
        if not listener:
            # nobody listening
            return
        self._forward(listener.download_failed, request)


class Batch(object):
    """
    Provides batch processing of a collection of content download requests.

    How it works:

      request-1 --> queue-1 (source-1)
        |              | <fail>
        |              |--> queue2  (source-2)
        |                     | <fail>
        |                     |--> queue-0  (primary)
        |                             | <succeeded>
        |                             |--> END
      request-2 --> queue-3 (source-3)
        |              | <fail>
        |              |--> queue4  (source-4)
        |                     | <fail>
        |                     |--> queue-0  (primary)
        |                             | <fail>
        |                             |--> END
      request-3 --> queue-0 (primary)
        |              | <succeeded>
        |              |--> END
      request-4 --> queue-3 (source-3)
        |              | <succeeded>
        |              |--> END
        ...

    :ivar _mutex: The object mutex.
    :type _mutex: RLock
    :ivar canceled: A cancel event.  Signals cancellation requested.
    :type canceled: threading.Event
    :ivar primary: A primary nectar downloader.  Used to download the
        requested content unit when it cannot be achieved using alternate content sources.
    :type primary: nectar.downloaders.base.Downloader
    :ivar sources: A dictionary of content sources keyed by source ID.
    :type sources: dict
    :ivar requests: An iterable of: pulp.server.content.sources.model.Request.
    :type requests: iterable
    :ivar listener: An optional download request listener.
    :type listener: Listener
    :ivar in_progress: A set of request object IDs used to detect when ALL processing has completed.
    :type in_progress: set
    :ivar queues: A dictionary of: RequestQueue keyed by source_id.
    :type queues: dict
    """

    def __init__(self, canceled, primary, sources, requests, listener):
        """
        :param canceled: A cancel event.  Signals cancellation requested.
        :type canceled: threading.Event
        :param primary: The *primary* content source used when requested content
            download requests cannot be satisfied using alternate content sources.
        :type primary: PrimarySource
        :param sources: A dictionary of content sources keyed by source ID.
        :type sources: dict
        :param requests: An iterable of: pulp.server.content.sources.model.Request.
        :type requests: iterable
        :param listener: An optional download request listener.
        :type listener: Listener
        """
        self._mutex = RLock()
        self.canceled = canceled
        self.primary = primary
        self.sources = sources
        self.requests = requests
        self.listener = listener
        self.in_progress = set()
        self.queues = {}

    @property
    def is_canceled(self):
        """
        Get whether the batch download has been canceled.
        :return: True if canceled.
        :rtype: bool.
        """
        return self.canceled.isSet()
    
    def dispatch(self, request):
        """
        Dispatch the specified request to the queue associated with the
        next content source that can satisfy the request.  The next source is
        determined by the request itself.  If the list of available sources
        is exhausted, the request is not dispatched.
        :param request: The request that has been stared.
        :type request: pulp.server.content.sources.model.Request
        :return: True if dispatched.
        :rtype: bool
        """
        dispatched = False
        try:
            source, url = request.sources.next()
            queue = self.find_queue(source)
            queue.put(Item(request, url))
            dispatched = True
        except StopIteration:
            self.finished(request)
        return dispatched

    def find_queue(self, source):
        """
        Find the request queue associated with the specified content source.
        The queue is created and added if not found.
        :param source: A content source.
        :type source: pulp.server.content.sources.model.ContentSource
        :return: The request queue.
        :rtype: RequestQueue
        """
        with self._mutex:
            try:
                return self.queues[source.id]
            except KeyError:
                return self._add_queue(source)
            
    def _add_queue(self, source):
        """
        Create a request queue for the specified content source and add
        it to the *sources* dictionary by source_id.
        :param source: A content source.
        :type source: pulp.server.content.sources.model.ContentSource
        :return: The added queue.
        :rtype: RequestQueue
        """
        queue = RequestQueue(self.canceled, source)
        queue.downloader.event_listener = NectarListener(self)
        self.queues[source.id] = queue
        queue.start()
        return queue

    def download(self):
        """
        Begin processing the batch of requests.
        Download files using available alternate content sources.
        An attempt is made to satisfy each download request using the alternate
        content sources in the order specified by priority.  The specified
        downloader is designated as the primary source and is used in the event that
        the request cannot be completed using alternate sources.
        :return: The download report.
        :rtype: DownloadReport
        """
        report = DownloadReport()
        report.total_sources = len(self.sources)

        try:
            for request in self.requests:
                if self.is_canceled:
                    # canceled
                    break
                request.find_sources(self.primary, self.sources)
                self.started(request)
                self.dispatch(request)
        except Exception:
            self.canceled.set()
            raise
        finally:
            while self.is_waiting():
                sleep(0.5)
            for queue in self.queues.values():
                queue.put(None)
                queue.halt()
            for queue in self.queues.values():
                queue.join()

        for source_id, queue in self.queues.items():
            listener = queue.downloader.event_listener
            downloads = report.downloads.setdefault(source_id, DownloadDetails())
            downloads.total_succeeded += listener.total_succeeded
            downloads.total_failed += listener.total_failed
        return report

    def started(self, request):
        """
        The specified request has been started and is in progress.
        :param request: The request that has been stared.
        :type request: pulp.server.content.sources.model.Request
        """
        self.in_progress.add(request)

    def finished(self, request):
        """
        The specified request has been completed and is no long in-progress.
        A request is *completed* when it has either succeeded or failed with
        no remaining content sources to try.
        :param request: The request that has been stared.
        :type request: pulp.server.content.sources.model.Request
        """
        self.in_progress.remove(request)

    def is_waiting(self):
        """
        Get whether the batch is waiting for all of the download
        requests be complete.
        """
        return not (self.is_canceled or len(self.in_progress) == 0)


#
# The object handled by the RequestQueue put() and get().
#
Item = namedtuple('Item', ['request', 'url'])


class RequestQueue(Thread):
    """
    A thread that associates a queue and a downloader.  The queue, wrapped in a
    generator, is passed to the downloader as the iterable of download requests.
    The StopIteration is raised when:
    - The end-of-queue marker (None) is queued.
    - The thread is halted by calling halt().
    :ivar _halted: Flag indicating that a thread halt has been requested.
    :type _halted: bool
    :ivar queue: Used to queue download requests between threads.
    :type queue: Queue
    :ivar downloader: A nectar downloader.
    :type downloader: nectar.downloaders.base.Downloader
    :ivar canceled: A cancel event.  Signals cancellation has been requested.
    :type canceled: threading.Event
    """

    def __init__(self, canceled, source):
        """
        :param canceled: A cancel event.  Signals cancellation requested.
        :type canceled: threading.Event
        :param source: A content source.
        :type source: ContentSource
        """
        super(RequestQueue, self).__init__(name=source.id)
        self._halted = False
        self.queue = Queue(source.max_concurrent)
        self.downloader = source.get_downloader()
        self.canceled = canceled
        self.setDaemon(True)

    @property
    def _run(self):
        """
        Get whether the thread should continue to run.
        Convenient method for checking the *canceled* event and the *_halted* flag.
        :return: True if should continue.
        :rtype: bool
        """
        return not (self.canceled.isSet() or self._halted)

    def put(self, item):
        """
        Add an item to the queue.
        An item of (None) is and end-of-queue marker.  This marker will cause
        The next() method to return with will cause StopIteration to be raised when
        the generator is being iterated.
        :param item: An item to queue.
        :return: Item
        """
        while self._run:
            try:
                self.queue.put(item, timeout=10)
                break
            except Full:
                # ignored
                pass

    def get(self):
        """
        Get the next item queued for download.
        :return: The next item queued for download.
        :rtype: Item
        """
        while self._run:
            try:
                return self.queue.get(timeout=10)
            except Empty:
                # ignored
                pass
        return None  # end-of-queue marker

    def run(self):
        """
        The thread main.
        """
        try:
            requests = NectarFeed(self)
            self.downloader.download(requests)
        except Exception:
            log.exception(self.getName())
            self.drain()

    def drain(self):
        """
        Read and fail all requests remaining in the queue.
        """
        for request in NectarFeed(self):
            report = NectarDownloadReport.from_download_request(request)
            self.downloader.fire_download_failed(report)

    def halt(self):
        """
        Halt the queue thread.
        """
        self._halted = True


class NectarFeed(object):
    """
    Provides a blocking download request feed to a nectar downloader.
    :param queue: A queue to drain.
    :type queue: RequestQueue
    """

    def __init__(self, queue):
        """
        :param queue: A queue to drain.
        :type queue: RequestQueue
        """
        self.queue = queue

    def __iter__(self):
        """
        Performs a get() on the queue until reaching the end-of-queue marker.
        :return: An iterable of: DownloadRequest.
        :rtype: iterable
        """
        while True:
            item = self.queue.get()
            if item is None:
                # end-of-queue marker
                return
            request = DownloadRequest(item.url, item.request.destination, data=item.request)
            yield request