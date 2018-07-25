import asyncio


async def create_pipeline(stages, in_q=None, maxsize=100):
    """
    Creates a Stages API linear pipeline from the list `stages` and return as a single coroutine.

    Each stage is a coroutine and reads from an input `asyncio.Queue` and writes to an output
    `asyncio.Queue`. When the stage is ready to shutdown it writes a `None` to the output Queue.
    Here is an example of the simplest stage that only passes data.

    >>> async def my_stage(in_q, out_q):
    >>>     while True:
    >>>         item = await in_q.get()
    >>>         if item is None:  # Check if the previous stage is shutdown
    >>>             break
    >>>         await out_q.put(item)
    >>>     await out_q.put(None)  # this stage is shutdown so send 'None'

    Args:
        stages (list of coroutines): A list of Stages API compatible coroutines.
        in_q (asyncio.Queue): The queue the first stage should read from. This is how to put work
            into the pipeline. Optional especially for cases where the first stage generates items
            for `out_q` without needing inputs from `in_q`.
        maxsize (int): The maximum amount of items a queue between two stages should hold. Optional
            and defaults to 100.

    Returns:
        A single coroutine that can be used to run, wait, or cancel the entire pipeline with.
    """
    futures = []
    for stage in stages:
        out_q = asyncio.Queue(maxsize=maxsize)
        futures.append(stage(in_q, out_q))
        in_q = out_q
    await asyncio.gather(*futures)


async def end_stage(in_q, out_q):
    """
    A Stages API stage that drains `in_q` and do nothing with the items. This is expected at the end
    of all pipelines.

    Without this stage, the maxsize of the `out_q` from the last stage could fill up and block the
    entire pipeline.
    """
    while True:
        content = await in_q.get()
        if content is None:
            break
