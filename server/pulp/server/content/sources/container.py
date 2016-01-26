from collections import namedtuple
from logging import getLogger
from threading import Thread, RLock
from Queue import Queue, Empty, Full

from nectar.listener import DownloadEventListener
from nectar.report import DownloadReport as NectarDownloadReport, DOWNLOAD_SUCCEEDED
from nectar.request import DownloadRequest

from pulp.server.content.sources.event import Started, Succeeded, Failed
from pulp.server.content.sources.model import ContentSource, PrimarySource, \
    DownloadReport, DownloadDetails, RefreshReport
from pulp.server.managers import factory as managers


log = getLogger(__name__)


class DownloadFailed(Exception):
    """
    A serial download has failed.
    """
    pass


class ContentContainer(object):
    """
    The content container represents a virtual collection of content that is
    supplied by a collection of content sources.  When using within reactor
    frameworks such as "Twisted", set threaded = False.

    :ivar sources: A dictionary of content sources keyed by source ID.
    :type sources: dict
    :ivar threaded: Use threaded download method (default:True).
    :type threaded: bool
    """

    def __init__(self, path=None, threaded=True):
        """
        :param path:     The absolute path to a directory containing
                         content source descriptor files.
        :type  path:     str
        :param threaded: Whether or not to use the threaded download method.
        :type  threaded: bool
        """
        self.sources = ContentSource.load_all(path)
        self.threaded = threaded

    def download(self, downloader, requests, listener=None):
        """
        Download files using available alternate content sources.
        An attempt is made to satisfy each download request using the alternate
        content sources in the order specified by priority.  The specified
        downloader is designated as the primary source and is used in the event that
        the request cannot be completed using alternate sources.

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
        self.refresh()
        primary = PrimarySource(downloader)
        if self.threaded:
            method = Threaded
        else:
            method = Serial
        batch = method(primary, self, requests, listener)
        report = batch()
        return report

    def refresh(self, force=False):
        """
        Refresh the content catalog using available content sources.

        :param force: Force refresh of content sources with unexpired catalog entries.
        :type force: bool
        :return: A list of refresh reports.
        :rtype: list of: pulp.server.content.sources.model.RefreshReport
        """
        reports = []
        catalog = managers.content_catalog_manager()
        for source_id, source in self.sources.items():
            if force or not catalog.has_entries(source_id):
                try:
                    report = source.refresh()
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


class NectarListener(DownloadEventListener):

    def __init__(self, batch):
        """
        :param batch: A download batch.
        :type batch: Threaded
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
        request = report.data
        listener = self.batch.listener
        event = Started(request)
        event(listener)

    def download_succeeded(self, report):
        """
        Nectar download succeeded.
        The associated request is marked as succeeded.
        Forwarded to the listener registered with the container.

        :param report: A nectar download report.
        :type report: nectar.report.DownloadReport
        """
        self.total_succeeded += 1
        request = report.data
        request.downloaded = True
        listener = self.batch.listener
        self.batch.in_progress.decrement()
        event = Succeeded(request)
        event(listener)

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
        request = report.data
        request.errors.append(report.error_msg)
        listener = self.batch.listener
        if self.batch.dispatch(request):
            # trying another
            return
        event = Failed(request)
        event(listener)


class Batch(object):
    """
    Provides batch processing of a collection of content download requests.

    :ivar primary: The *primary* content source used when requested content
        download requests cannot be satisfied using alternate content sources.
    :type primary: PrimarySource
    :ivar container: A content container.
    :type container: ContentContainer
    :ivar requests: An iterable of: pulp.server.content.sources.model.Request.
    :type requests: iterable
    :ivar listener: An optional download request listener.
    :type listener: Listener
    """

    def __init__(self, primary, container, requests, listener):
        """
        :param primary: The *primary* content source used when requested content
            download requests cannot be satisfied using alternate content sources.
        :type primary: PrimarySource
        :param container: A content container.
        :type container: ContentContainer
        :param requests: An iterable of: pulp.server.content.sources.model.Request.
        :type requests: iterable
        :param listener: An optional download request listener.
        :type listener: Listener
        """
        self.primary = primary
        self.container = container
        self.requests = requests
        self.listener = listener

    @property
    def sources(self):
        """
        The list of available sources.

        :return: The list of available sources.
        :rtype: list
        """
        return self.container.sources

    def __call__(self):
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
        raise NotImplementedError()


class Serial(Batch):
    """
    Provides sequential batch processing of a collection of content download requests.
    This approach does *not* use threading.
    """

    def __call__(self):
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
        for request in self.requests:
            event = Started(request)
            event(self.listener)
            request.find_sources(self.primary, self.sources)
            for source, url in request.sources:
                details = report.downloads.setdefault(source.id, DownloadDetails())
                try:
                    self._download(url, request.destination, source)
                    details.total_succeeded += 1
                    request.downloaded = True
                    event = Succeeded(request)
                    event(self.listener)
                    break
                except DownloadFailed, df:
                    request.errors.append(str(df))
                    details.total_failed += 1
            if request.downloaded:
                continue
            event = Failed(request)
            event(self.listener)
        return report

    def _download(self, url, destination, source):
        """
        Download the URL using the source.

        :param source: A content source used for the download.
        :type source: ContentSource
        :param url: The URL of the file to be downloaded.
        :type url: str
        :param destination: The absolute path to where the file is
            to be downloaded.
        :type destination: str
        :return: The result: (succeeded, error-message)
        :rtype: tuple
        """
        request = DownloadRequest(url, destination)
        downloader = source.get_downloader(self.primary.session)
        report = downloader.download_one(request, events=True)
        if report.state == DOWNLOAD_SUCCEEDED:
            # All good
            return
        else:
            raise DownloadFailed(report.error_msg)


class Threaded(Batch):
    """
    Provides threaded batch processing of a collection of content download requests.

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

    :ivar primary: A primary nectar downloader.  Used to download the
        requested content unit when it cannot be achieved using alternate content sources.
    :type primary: nectar.downloaders.base.Downloader
    :ivar container: A content container.
    :type container: ContentContainer
    :ivar requests: An iterable of: pulp.server.content.sources.model.Request.
    :type requests: iterable
    :ivar listener: An optional download request listener.
    :type listener: Listener
    :ivar in_progress: Tracker used to detect when ALL processing has completed.
    :type in_progress: Tracker
    :ivar queues: A dictionary of: RequestQueue keyed by source_id.
    :type queues: dict
    """

    def __init__(self, primary, container, requests, listener):
        """
        :param primary: The *primary* content source used when requested content
            download requests cannot be satisfied using alternate content sources.
        :type primary: PrimarySource
        :param container: A content container.
        :type container: ContentContainer
        :param requests: An iterable of: pulp.server.content.sources.model.Request.
        :type requests: iterable
        :param listener: An optional download request listener.
        :type listener: Listener
        """
        super(Threaded, self).__init__(primary, container, requests, listener)
        self._mutex = RLock()
        self.in_progress = Tracker()
        self.queues = {}

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
            self.in_progress.decrement()
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
        queue = RequestQueue(source, self.primary.session)
        queue.downloader.event_listener = NectarListener(self)
        self.queues[source.id] = queue
        queue.start()
        return queue

    def __call__(self):
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
        count = 0
        report = DownloadReport()
        report.total_sources = len(self.sources)

        try:
            for request in self.requests:
                request.find_sources(self.primary, self.sources)
                self.dispatch(request)
                count += 1
        finally:
            self.in_progress.wait(count)
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


# The object handled by the RequestQueue put() and get().
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
    """

    def __init__(self, source, session):
        """
        :param source: A content source.
        :type source: ContentSource
        :param session: An http session.
        :type session: requests.Session
        """
        super(RequestQueue, self).__init__(name=source.id)
        self._halted = False
        self.queue = Queue(source.max_concurrent)
        self.downloader = source.get_downloader(session)
        self.setDaemon(True)

    def put(self, item):
        """
        Add an item to the queue.
        An item of (None) is and end-of-queue marker.  This marker will cause
        The next() method to return with will cause StopIteration to be raised when
        the generator is being iterated.

        :param item: An item to queue.
        :return: Item
        """
        while not self._halted:
            try:
                self.queue.put(item, timeout=3)
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
        while not self._halted:
            try:
                return self.queue.get(timeout=3)
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


class Tracker(object):
    """
    A *decrement* event tracker.

    :ivar queue: A queue containing *decrement* token.
    :type queue: Queue
    """

    def __init__(self):
        self.queue = Queue()

    def decrement(self):
        """
        Add a *decrement* token.
        """
        self.queue.put(0)

    def wait(self, count):
        """
        Wait for the specified number of *decrement* tokens.

        :param count: The number of expected *decrement* tokens.
        :type: count: int
        """
        if count < 0:
            raise ValueError('must be >= 0')
        while count > 0:
            try:
                self.queue.get(timeout=3)
                count -= 1
            except Empty:
                # ignored
                pass
