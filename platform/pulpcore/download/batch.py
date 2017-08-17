from concurrent.futures import ThreadPoolExecutor
from gettext import gettext as _
from logging import getLogger, DEBUG
from queue import Queue, Empty
from threading import Thread, current_thread

from .single import Context


# The default queuing backlog.
BACKLOG = 1024
# The default concurrency.
CONCURRENT = 4


log = getLogger(__name__)


class Batch:
    """
    Provides batching and concurrent execution of downloads.

    Attributes:
        downloads (collections.abc.Iterable): An Iterable of downloads.
        concurrent (int): The number of downloads to execute in concurrently.
        iterator (PlanIterator): Used to iterate downloads as they complete.
        context (SharedContext): A shared download context.
        feeder (DownloadFeeder): Used to feed submit downloads to the executor.
        _is_shutdown (bool): Batch has been shutdown.

    Notes:
        * The batch should be used as a context manager.
        * Or, `shutdown()` must be called manually.

    Examples:

        >>>
        >>> from pulpcore.download import Batch, HttpDownload, DownloadError
        >>>
        >>> url = 'http://content.org/dog.rpm'
        >>> path = '/tmp/working/dog.rpm'
        >>> downloads = (HttpDownload(url, path) for _ in range(10))
        >>>
        >>> with Batch(downloads) as batch:
        >>>     for plan in batch():
        >>>         try:
        >>>             plan.result()
        >>>         except DownloadError:
        >>>             # An error occurred.
        >>>         else:
        >>>             # Use the downloaded file \o/
        >>>
    """

    def __init__(self, downloads, concurrent=CONCURRENT, backlog=BACKLOG, context=None):
        """
        Args:
            downloads (collections.abc.Iterable): An Iterable of downloads.
            concurrent (int): The number of downloads to execute in concurrently.
            backlog (int): The number of downloads kept in memory.
            context (SharedContext): An (optional) shared download context.

        Raises:
            ValueError: concurrent less than 2 or backlog is less than concurrent.
        """
        super(Batch, self).__init__()
        self.downloads = downloads
        self.concurrent = concurrent
        self.iterator = PlanIterator(backlog)
        self.executor = BatchExecutor(concurrent=concurrent, backlog=backlog)
        self.context = context or Context()
        self.feeder = DownloadFeeder(self)
        self._is_shutdown = False

    @property
    def is_shutdown(self):
        """
        Returns:
            bool: Batch has been shutdown.
        """
        return self._is_shutdown

    def download(self):
        """
        Execute all of the downloads.

        Returns:
            PlanIterator: A plan iterator.
                The iterator will yield the download `Plan` in the order completed.
        """
        log.debug(_('%(batch)s - download started'), {'batch': self})
        self.feeder.start()
        return self.iterator

    def shutdown(self):
        """
        End processing and shutdown the feeder and the thread pool.

        Notes:
            This must be called to prevent leaking resources unless the Batch
            is used as a context manager.

        Examples:
            >>>
            >>> with Batch(..) as batch:
            >>>    # ...
        """
        if self._is_shutdown:
            return
        self._is_shutdown = True
        log.debug(_('%(batch)s - shutdown'), {'batch': self})
        self.feeder.shutdown()
        self.executor.shutdown()

    def __call__(self):
        """
        Execute all of the downloads.
        Calls `download()`.

        Returns:
            PlanIterator: A plan iterator.
                The iterator will yield the download `Plan` in the order completed.
        """
        return self.download()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        try:
            self.shutdown()
        except Exception:
            if log.isEnabledFor(DEBUG):
                log.exception(_('Batch shutdown failed.'))

    def __str__(self):
        _id = str(id(self))[-4:]
        return _('Batch: id={s} concurrent={c}').format(s=_id, c=self.concurrent)


class BatchExecutor(ThreadPoolExecutor):
    """
    Batch thread pool executor.
    """

    def __init__(self, concurrent=CONCURRENT, backlog=BACKLOG):
        """
        A thread pool executor tailored for the batch.
        The worker queue size is restricted to limit memory footprint.

        Args:
            concurrent (int): The number of downloads to execute in concurrently.
            backlog (int): The number of downloads kept in memory.

        Raises:
            ValueError: concurrent less than 2 or backlog is less than concurrent.
        """
        super(BatchExecutor, self).__init__(max_workers=concurrent)
        self._work_queue = Queue(maxsize=backlog)
        if concurrent < 2:
            raise ValueError(_('concurrent may not be < 2'))
        if backlog < concurrent:
            raise ValueError(_('backlog may not be < concurrent'))


class DownloadFeeder(Thread):
    """
    Download feeder.
    A thread used to feed each batched download into the executor.
    May be interrupted and terminated by calling shutdown().

    Attributes:
        batch (Batch): A batch to feed.
        total (int): The total number of downloads queued.
        is_shutdown (bool): Feeder has been shutdown.
    """

    def __init__(self, batch):
        super(DownloadFeeder, self).__init__(name='feeder')
        self.batch = batch
        self.daemon = True
        self.total = 0
        self.is_shutdown = False

    @property
    def iterator(self):
        return self.batch.iterator

    @property
    def executor(self):
        return self.batch.executor

    @property
    def downloads(self):
        return self.batch.downloads

    @property
    def context(self):
        return self.batch.context

    def shutdown(self, wait=True):
        """
        Shutdown.
        Abort feeding and terminate.

        Args:
            wait (bool): Wait for thread to terminate.
        """
        if self.is_shutdown:
            return
        self.is_shutdown = True
        if wait:
            self.join()

    def run(self):
        """
        Thread (main) loop.
        Submit each download to the batch executor.
        """
        try:
            for download in self.downloads:
                if self.is_shutdown:
                    return
                log.debug(
                    _('%(feeder)s - feed #%(total)d url=%(url)s'),
                    {
                        'feeder': self,
                        'total': self.total,
                        'url': download.url
                    })
                download.context = self.context
                future = self.executor.submit(Plan(self.batch, download))
                future.add_done_callback(self.iterator.add)
                self.total += 1
        except Exception as e:
            log.exception(_('feeder failed.'))
            self.iterator.raised(e)
            self.total += 1
        finally:
            self.done()

    def done(self):
        """
        Done feeding downloads and need to update the iterator appropriately.
        """
        if self.total:
            self.iterator.total = self.total
        else:
            self.iterator.drain()

    def __str__(self):
        _id = str(id(self))[-4:]
        return _('DownloadFeeder: id={s} shutdown={a}').format(s=_id, a=self.is_shutdown)


class QueueIterator:
    """
    A Queue iterator.
    Each item in the queue is a tuple of: (code, payload).

    Attributes:
        queue (Queue): The input queue to be iterated.
        iterated (int): The number of times `__next__()` was called.
        total (int): The total number queued.  A value of `-1` indicates
            the total is not yet known.
    """

    NEXT = 'NEXT'
    EXCEPTION = 'EXCEPTION'
    END = 'END'

    def __init__(self, backlog=BACKLOG):
        self.queue = Queue(maxsize=backlog)
        self.iterated = 0
        self.total = -1

    def put(self, code, payload=None, block=True):
        """
        Enqueue a message.

        Args:
            code (str): The message code.
            payload (object): The message payload.
            block (bool): Block when queue is full (default:True).
        """
        log.debug(
            _('%(iterator)s put: code=%(code)s payload=%(payload)s'),
            {
                'iterator': self,
                'code': code,
                'payload': payload
            })
        message = (code, payload)
        self.queue.put(message, block=block)

    def add(self, payload):
        """
        Add the next object to the input queue to be rendered by `__next__()`.

        Args:
            payload: An object to be rendered by `__next__()`.
        """
        self.put(self.NEXT, payload)

    def raised(self, exception):
        """
        Add a fatal exception to the input queue.  The exception has been raised by
        the object providing the objects to be iterated.

        Args:
            exception: An exception to be raised by `__next__()`.
        """
        self.put(self.EXCEPTION, exception)

    def drain(self):
        """:
        Drain the input queue.
        Add an message to the input queue that signals that the input
        queue will always be empty.  The object feeding the queue has nothing
        to be iterated.
        """
        log.debug(_('%(iterator)s - input drained'), {'iterator': self})
        while True:
            try:
                self.queue.get(block=False)
            except Empty:
                break
        self.end()

    def end(self):
        """
        Add an message to the input queue that marks the end of input.
        """
        self.put(self.END)

    def __next__(self):
        """
        Get the next enqueued object.

        Returns:
            The next enqueued object.

        Raises:
            StopIteration: when finished iterating.
        """
        log.debug(_('%(iterator)s - next'), {'iterator': self})

        if self.iterated == self.total:
            raise StopIteration()

        code, payload = self.queue.get()

        log.debug(
            _('%(iterator)s next: code=%(code)s payload=%(payload)s'),
            {
                'iterator': self,
                'code': code,
                'payload': payload
            })

        # next
        if code == self.NEXT:
            self.iterated += 1
            return payload
        # fatal
        if code == self.EXCEPTION:
            raise payload
        # empty
        if code == self.END:
            raise StopIteration()

    def __iter__(self):
        return self

    def __str__(self):
        _id = str(id(self))[-4:]
        description = _('Iterator: id={s} iterated={i}/{t}')
        return description.format(
            s=_id,
            i=self.iterated,
            t=self.total)


class FutureIterator(QueueIterator):
    """
    A queue iterator that expects the payload to be a `concurrent.futures.Future`.
    """

    def __next__(self):
        """
        Get the next future and propagate any raised exceptions.

        Returns:
            The next `Future.result()`

        Raises:
            Anything raised by the object executed.
        """
        future = super(FutureIterator, self).__next__()
        try:
            return future.result()
        except Exception as exception:
            log.debug(
                _('%(iterator)s - raising: %(exception)s'),
                {
                    'iterator': self,
                    'exception': exception
                })
            raise


class PlanIterator(FutureIterator):
    """
    Batched download plan iterator.
    """

    def __next__(self):
        """
        Get the next completed download plan and propagate any raised exceptions.

        Returns:
            Plan: The next completed download execution plan.

        Raises:
            Anything raised by the object executed.
        """
        while True:
            download = super(PlanIterator, self).__next__()
            if download:
                return download


class Plan:
    """
    Batch download execution plan.
    The plan provides:
      - Ensure self is returned in the future.result.
      - Catch and store exceptions raised by the download. This ensure that
        only fatal batch framework exceptions are raised during iteration.

    Attributes:
        batch (pulpcore.download.Batch): The batch.
        download (pulpcore.download.Download): The wrapped download.
        executed (bool): Indicates the plan has been executed.
        error (Exception): An exception raised by the download.
    """

    def __init__(self, batch, download):
        """

        Args:
            batch (pulpcore.download.Batch): The batch.
            download (pulpcore.download.Download): The wrapped download.
        """
        self.batch = batch
        self.download = download
        self.executed = False
        self.error = None

    def result(self):
        """
        Get the execution result.
        This **should** be called to ensure that error cases are properly handled.

        Returns:
            pulpcore.download.Download: The planned download.

        Raises:
            Exception: Any exception raised during the download.
        """
        if self.error is None:
            return self.download
        else:
            raise self.error

    def __call__(self):
        """
        Execute the plan.

        Returns:
            Plan: self
        """
        if self.batch.is_shutdown:
            return

        with self as download:
            self.executed = True
            try:
                download()
            except Exception as error:
                self.error = error
        return self

    def __enter__(self):
        thread = current_thread()
        log.debug(
            _('%(download)s thread=%(thread)s - started'),
            {
                'thread': thread.getName(),
                'download': self
            })
        return self.download

    def __exit__(self, *unused):
        thread = current_thread()
        log.debug(
            _('%(download)s thread=%(thread)s - end'),
            {
                'thread': thread.getName(),
                'download': self
            })

    def __str__(self):
        return _(
            'Plan: {download} executed: {executed} error: {error}'.format(
                download=self.download,
                executed=self.executed,
                error=self.error))
