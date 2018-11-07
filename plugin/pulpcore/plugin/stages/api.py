import asyncio
from gettext import gettext as _

from django.conf import settings

from .profiler import ProfilingQueue


class Stage:
    """
    The base class for all Stages API stages.

    To make a stage, inherit from this class and implement :meth:`__call__` on the subclass.
    """

    async def __call__(self, in_q, out_q):
        """
        The coroutine that is run as part of this stage.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive items from the previous stage.
            out_q (:class:`asyncio.Queue`): The queue to put handled items into for the next stage.

        Returns:
            The coroutine that runs this stage.

        """
        raise NotImplementedError(_('A plugin writer must implement this method'))

    @staticmethod
    async def batches(in_q, minsize=50):
        """
        Asynchronous iterator yielding batches of :class:`DeclarativeContent` from `in_q`.

        The iterator will try to get as many instances of
        :class:`DeclarativeContent` as possible without blocking, but
        at least `minsize` instances.

        Args:
            in_q (:class:`asyncio.Queue`): The queue to receive
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects from.
            minsize (int): The minimum batch size to yield (unless it is the final batch)

        Yields:
            A list of :class:`DeclarativeContent` instances

        Examples:
            Used in stages to get large chunks of declarative_content instances from
            `in_q`::

                class MyStage(Stage):
                    async def __call__(self, in_q, out_q):
                        async for batch in self.batches(in_q):
                            for declarative_content in batch:
                                # process declarative content
                                await out_q.put(declarative_content)
                        await out_q.put(None)

        """
        batch = []
        shutdown = False

        def add_to_batch(batch, content):
            if content is None:
                return True
            batch.append(content)
            return False

        while not shutdown:
            content = await in_q.get()
            shutdown = add_to_batch(batch, content)
            while not shutdown:
                try:
                    content = in_q.get_nowait()
                except asyncio.QueueEmpty:
                    break
                else:
                    shutdown = add_to_batch(batch, content)

            if batch and (len(batch) >= minsize or shutdown):
                yield batch
                batch = []


async def create_pipeline(stages, maxsize=100):
    """
    A coroutine that builds a Stages API linear pipeline from the list `stages` and runs it.

    Each stage is a coroutine and reads from an input :class:`asyncio.Queue` and writes to an output
    :class:`asyncio.Queue`. When the stage is ready to shutdown it writes a `None` to the output
    queue. Here is an example of the simplest stage that only passes data.

    >>> async def my_stage(in_q, out_q):
    >>>     while True:
    >>>         item = await in_q.get()
    >>>         if item is None:  # Check if the previous stage is shutdown
    >>>             break
    >>>         await out_q.put(item)
    >>>     await out_q.put(None)  # this stage is shutdown so send 'None'

    Args:
        stages (list of coroutines): A list of Stages API compatible coroutines.
        maxsize (int): The maximum amount of items a queue between two stages should hold. Optional
            and defaults to 100.

    Returns:
        A single coroutine that can be used to run, wait, or cancel the entire pipeline with.
    """
    futures = []
    if settings.PROFILE_STAGES_API:
        in_q = ProfilingQueue.make_and_record_queue(stages[0], 0, maxsize)
        for i, stage in enumerate(stages):
            next_stage_num = i + 1
            if next_stage_num == len(stages):
                out_q = None
            else:
                next_stage = stages[next_stage_num]
                out_q = ProfilingQueue.make_and_record_queue(next_stage, next_stage_num, maxsize)
            futures.append(asyncio.ensure_future(stage(in_q, out_q)))
            in_q = out_q
    else:
        in_q = None
        for stage in stages:
            out_q = asyncio.Queue(maxsize=maxsize)
            futures.append(asyncio.ensure_future(stage(in_q, out_q)))
            in_q = out_q

    try:
        await asyncio.gather(*futures)
    except Exception:
        # One of the stages raised an exception, cancel all stages...
        pending = []
        for task in futures:
            if not task.done():
                task.cancel()
                pending.append(task)
        # ...and run until all Exceptions show up
        if pending:
            await asyncio.wait(pending, timeout=60)
        raise


class EndStage(Stage):
    """
    A Stages API stage that drains `in_q` and does nothing with the items. This is required at the
    end of all pipelines.

    Without this stage, the `maxsize` of the last stage's `out_q` could fill up and block the entire
    pipeline.
    """

    async def __call__(self, in_q, out_q):
        while True:
            content = await in_q.get()
            if content is None:
                break
