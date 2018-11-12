import asyncio

import asynctest

from pulpcore.plugin.stages import Stage


class TestStage(asynctest.TestCase):

    async def test_none_only(self):
        in_q = asyncio.Queue()
        in_q.put_nowait(None)
        batch_it = Stage.batches(in_q, minsize=1)
        with self.assertRaises(StopAsyncIteration):
            await batch_it.__anext__()

    async def test_single_batch_and_none(self):
        in_q = asyncio.Queue()
        in_q.put_nowait(1)
        in_q.put_nowait(2)
        in_q.put_nowait(None)
        batch_it = Stage.batches(in_q, minsize=1)
        self.assertEqual([1, 2], await batch_it.__anext__())
        with self.assertRaises(StopAsyncIteration):
            await batch_it.__anext__()

    async def test_batch_and_single_none(self):
        in_q = asyncio.Queue()
        in_q.put_nowait(1)
        in_q.put_nowait(2)
        batch_it = Stage.batches(in_q, minsize=1)
        self.assertEqual([1, 2], await batch_it.__anext__())
        in_q.put_nowait(None)
        with self.assertRaises(StopAsyncIteration):
            await batch_it.__anext__()

    async def test_two_batches(self):
        in_q = asyncio.Queue()
        in_q.put_nowait(1)
        in_q.put_nowait(2)
        batch_it = Stage.batches(in_q, minsize=1)
        self.assertEqual([1, 2], await batch_it.__anext__())
        in_q.put_nowait(3)
        in_q.put_nowait(4)
        in_q.put_nowait(None)
        self.assertEqual([3, 4], await batch_it.__anext__())
        with self.assertRaises(StopAsyncIteration):
            await batch_it.__anext__()

    async def first_stage(self, out_q, num, minsize):
        for i in range(num):
            await asyncio.sleep(0)  # Force reschedule
            await out_q.put(i)
        await out_q.put(None)

    async def middle_stage(self, in_q, out_q, num, minsize):
        async for batch in Stage.batches(in_q, minsize):
            self.assertTrue(batch)
            self.assertGreaterEqual(len(batch), min(minsize, num))
            num -= len(batch)
            for b in batch:
                await out_q.put(b)
        self.assertEqual(num, 0)
        await out_q.put(None)

    async def last_stage(self, in_q, num, minsize):
        async for batch in Stage.batches(in_q, minsize):
            self.assertTrue(batch)
            self.assertGreaterEqual(len(batch), min(minsize, num))
            num -= len(batch)
        self.assertEqual(num, 0)

    async def test_batch_queue_and_min_sizes(self):
        """Test batches iterator in a small stages setting with various sizes"""
        for num in range(10):
            for minsize in range(1, 5):
                for qsize in range(1, num + 1):
                    q1 = asyncio.Queue(maxsize=qsize)
                    q2 = asyncio.Queue(maxsize=qsize)
                    await asyncio.gather(
                        self.last_stage(q2, num, minsize),
                        self.middle_stage(q1, q2, num, minsize),
                        self.first_stage(q1, num, minsize)
                    )
