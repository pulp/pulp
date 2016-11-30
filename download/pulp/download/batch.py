from concurrent.futures import ThreadPoolExecutor
from queue import Queue


# The default queuing backlog.
BACKLOG = 1024
# The default concurrency.
CONCURRENT = 10


class Batch:
    """
    Provides batching and concurrent execution of download requests.

    Attributes:
        requests (generator): A generator of requests.
        executor (ThreadPoolExecutor): The thread pool.
        scratchpad (dict): A scratchpad for sharing information with requests.

    Notes:
        * The batch should be used as a context manager.
        * Or, `end()` must be called manually.

    Examples:

        >>>
        >>> from pulp.download import Batch, HttpRequest
        >>>
        >>> url = 'http://redhat.com/content/great.rpm'
        >>> destination = '/tmp/working/great.rpm'
        >>> requests = (HttpRequest(url, destination) for _ in range(10))
        >>>
        >>> with Batch(requests) as batch:
        >>>     for request in batch.download():
        >>>         if request.succeeded():
        >>>             # Use the downloaded file
        >>>         else:
        >>>             # Log something
        >>>

    """

    def __init__(self, requests, concurrent=CONCURRENT, **scratchpad):
        """
        Args:
            requests (generator): A generator of requests.
            concurrent (int): The number of requests to execute in concurrently.
            **scratchpad (dict): A scratchpad for sharing information with requests.

        """
        super(Batch, self).__init__()
        self.requests = requests
        self.executor = ThreadPoolExecutor(max_workers=concurrent)
        self.executor.queue = Queue(maxsize=concurrent)
        self.scratchpad = scratchpad

    def download(self, backlog=BACKLOG):
        """
        Download the batch by executing all of the requests.

        Args:
            backlog (int): The number of download requests in memory.

        Returns:
            RequestIterator: A request iterator.
                The iterator will render the requests in the order completed.

        """
        iterator = RequestIterator(backlog)
        self.executor.submit(self._feed, iterator)
        return iterator

    def _feed(self, iterator):
        n = 0
        try:
            scratchpad = self.scratchpad
            for request in self.requests:
                scratchpad.update(request.scratchpad)
                request.scratchpad = scratchpad
                future = self.executor.submit(BatchRequest(request))
                future.add_done_callback(iterator.add)
                n += 1
        except Exception as e:
            iterator.raised(e)
            n += 1
        if n:
            iterator.total = n
        else:
            iterator.empty()

    def end(self):
        """
        End processing and shutdown the thread pool.

        Notes:
            This must be called to prevent leaking resources unless the Batch
            is used as a context manager.
            >>>
            >>> with Batch(..) as batch:
            >>>    # ...

        """
        self.executor.shutdown()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.end()


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

    NEXT = 0x00
    EXCEPTION = 0x02
    EMPTY = 0x03

    def __init__(self, backlog=BACKLOG):
        self.queue = Queue(maxsize=backlog)
        self.iterated = 0
        self.total = -1

    def add(self, payload):
        """
        Add the next object to the input queue to be rendered by `__next__()`.

        Args:
            payload: An object to be rendered by `__next__()`.

        """
        self.queue.put((QueueIterator.NEXT, payload))

    def raised(self, exception):
        """
        Add a fatal exception to the input queue.  The exception has been raised by
        the object providing the objects to be iterated.

        Args:
            exception: An exception to be raised by `__next__()`.

        """
        self.queue.put((QueueIterator.EXCEPTION, exception))

    def empty(self):
        """
        Add an message to the input queue that signals that the input
        queue will always be empty.  The object feeding the queue has nothing
        to be iterated.
        """
        self.queue.put((QueueIterator.EMPTY, None))

    def __next__(self):
        """
        Get the next enqueued object.

        Returns:
            The next enqueued object.

        Raises:
            StopIteration: when finished iterating.

        """
        if self.iterated == self.total:
            raise StopIteration()

        code, payload = self.queue.get()

        # next
        if code == QueueIterator.NEXT:
            self.iterated += 1
            return payload
        # fatal
        if code == QueueIterator.EXCEPTION:
            raise payload
        # empty
        if code == QueueIterator.EMPTY:
            raise StopIteration()

    def __iter__(self):
        return self


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
        exception = future.exception()
        if exception:
            raise exception
        else:
            return future.result()


class RequestIterator(FutureIterator):
    """
    Provided for semantic clarity.
    """
    pass


class BatchRequest:

    def __init__(self, request):
        self.request = request

    def __call__(self):
        self.request()
        return self.request
