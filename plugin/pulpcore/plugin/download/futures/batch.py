from collections import Iterator
from concurrent.futures import ThreadPoolExecutor
from gettext import gettext as _
from logging import getLogger
from queue import Queue
from threading import RLock, current_thread

from .single import Context


# The default number of downloads to be executed concurrently.
CONCURRENT = 4


log = getLogger(__name__)


class Batch:
    """
    Provides batching and concurrent execution of downloads.

    Attributes:
        downloads (collections.abc.Iterable): An Iterable of downloads.
        concurrent (int): The number of downloads to be executed concurrently.
        iterator (PlanIterator): Used to iterate downloads as they complete.
        context (SharedContext): A shared download context.

    Examples:

        >>>
        >>> from pulpcore.plugin.download.futures import Batch, HttpDownload, DownloadError
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

    def __init__(self, downloads, concurrent=CONCURRENT, context=None):
        """
        Args:
            downloads (collections.abc.Iterable): An Iterable of downloads.
            concurrent (int): The number of downloads to be executed concurrently.
            context (SharedContext): An (optional) shared download context.
        """
        super(Batch, self).__init__()
        self.downloads = iter(downloads)
        self.concurrent = concurrent
        self.iterator = PlanIterator()
        self.executor = ThreadPoolExecutor(max_workers=concurrent)
        self.context = context or Context()
        self._lock = RLock()

    def submit(self, plan):
        """
        Submit the plan for execution and increment `outstanding`.

        Args:
            plan (Plan): The plan to submit.
        """
        download = plan.download
        download.context = self.context
        future = self.executor.submit(plan)
        future.add_done_callback(self.completed)
        future.add_done_callback(self.iterator.add)
        self.iterator.outstanding += 1

    def completed(self, plan):
        """
        A plan has completed.

        Args:
            plan (Plan): The completed plan.
        """
        with self._lock:
            for download in self.downloads:
                plan = Plan(download)
                self.submit(plan)
                break

    def download(self):
        """
        Execute all of the downloads.

        Returns:
            PlanIterator: A plan iterator.
                The iterator will yield the download `Plan` in the order completed.
        """
        log.debug(_('%(batch)s - download started'), {'batch': self})
        with self._lock:
            for i, download in enumerate(self.downloads):
                plan = Plan(download)
                self.submit(plan)
                if i > (self.concurrent * 10):
                    break
        return self.iterator

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
        pass

    def __str__(self):
        _id = str(id(self))[-4:]
        return _(
            'Batch: id={s} concurrent={c} outstanding={o}').format(
                s=_id,
                c=self.concurrent,
                o=self.iterator.outstanding)


class PlanIterator(Iterator):
    """
    Batched download plan iterator.

    Attributes:
        queue (Queue): The input queue to be iterated.
        outstanding (int): Total number of downloads in the pipeline.
    """

    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self.outstanding = 0

    def add(self, future):
        """
        Add a future to be emitted by `__next__()`.

        Args:
            future (concurrent.futures.Future): A completed future.
        """
        log.debug(
            _('%(iterator)s put: future=%(future)s'),
            {
                'iterator': self,
                'future': future
            })
        self.queue.put(future)

    def __next__(self):
        """
        Get the next completed plan.

        Returns:
            Plan: The next completed object.

        Raises:
            StopIteration: when finished iterating.
        """
        if self.outstanding <= 0:
            raise StopIteration()

        log.debug(_('%(iterator)s - next'), {'iterator': self})

        future = self.queue.get()

        try:
            plan = future.result()
        except Exception as exception:
            log.debug(
                _('%(iterator)s - raising: %(exception)s'),
                {
                    'iterator': self,
                    'exception': exception
                })
            raise
        else:
            self.outstanding -= 1
            return plan

    def __iter__(self):
        return self


class Plan:
    """
    Batch download execution plan.
    The plan provides:
      - Ensure self is returned in the future.result.
      - Catch and store exceptions raised by the download. This ensure that
        only fatal batch framework exceptions are raised during iteration.

    Attributes:
        download (pulpcore.plugin.download.futures.Download): The planned download.
        executed (bool): Indicates the plan has been executed.
        error (Exception): An exception raised by the download.
    """

    def __init__(self, download):
        """

        Args:
            download (pulpcore.plugin.download.futures.Download): The planned download.
        """
        self.download = download
        self.executed = False
        self.error = None

    def result(self):
        """
        Get the execution result.
        This **should** be called to ensure that error cases are properly handled.

        Returns:
            pulpcore.plugin.download.futures.Download: The planned download.

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
