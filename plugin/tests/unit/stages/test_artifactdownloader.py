import asyncio

import asynctest
from unittest import mock

from pulpcore.plugin.stages import DeclarativeContent, DeclarativeArtifact
from pulpcore.plugin.stages.artifact_stages import ArtifactDownloader


class DownloaderMock:
    """Mock for a Downloader.

    URLs are expected to be the delay to wait to simulate downloading,
    e.g `url='5'` will wait for 5 seconds. `DownloaderMock` manages _global_
    statistics about the downloads.
    """
    running = 0
    downloads = 0
    canceled = 0

    def __init__(self, url, **kwargs):
        self.url = url

    @classmethod
    def reset(cls):
        cls.running = 0
        cls.downloads = 0
        cls.canceled = 0

    async def run(self, extra_data=None):
        DownloaderMock.running += 1
        try:
            await asyncio.sleep(int(self.url))
        except asyncio.CancelledError:
            DownloaderMock.running -= 1
            DownloaderMock.canceled += 1
            raise
        DownloaderMock.running -= 1
        DownloaderMock.downloads += 1
        result = mock.Mock()
        result.url = self.url
        result.artifact_attributes = {}
        return result


class TestArtifactDownloader(asynctest.ClockedTestCase):

    def setUp(self):
        super().setUp()
        DownloaderMock.reset()
        self.now = 0

    async def advance_to(self, now):
        delta = now - self.now
        assert delta >= 0
        await self.advance(delta)
        self.now = now

    async def advance(self, delta):
        await super().advance(delta)
        self.now += delta

    def queue_dc(self, in_q, delays=[]):
        """Put a DeclarativeContent instance into `in_q`

        For each `delay` in `delays`, associate a DeclarativeArtifact
        with download duration `delay` to the content unit. `delay ==
        None` means that the artifact is already present (pk is set)
        and no download is required.
        """
        das = []
        for delay in delays:
            artifact = mock.Mock()
            artifact.pk = True if delay is None else None
            artifact.DIGEST_FIELDS = []
            remote = mock.Mock()
            remote.get_downloader = DownloaderMock
            das.append(DeclarativeArtifact(artifact=artifact, url=str(delay),
                                           relative_path='path', remote=remote))
        dc = DeclarativeContent(content=mock.Mock(), d_artifacts=das)
        in_q.put_nowait(dc)

    async def download_task(self, in_q, out_q, max_concurrent_content=3):
        """
        A coroutine running the downloader stage with a mocked ProgressBar.

        Returns:
            The done count of the ProgressBar.
        """
        with mock.patch('pulpcore.plugin.stages.artifact_stages.ProgressBar') as pb:
            pb.return_value.__enter__.return_value.done = 0
            ad = ArtifactDownloader(max_concurrent_content=max_concurrent_content)
            await ad(in_q, out_q)
        return pb.return_value.__enter__.return_value.done

    async def test_downloads(self):
        in_q = asyncio.Queue()
        out_q = asyncio.Queue()
        download_task = self.loop.create_task(self.download_task(in_q, out_q))

        # Create 28 content units, every third one must be downloaded.
        # The downloads take 0, 3, 6,..., 27 seconds; content units
        # 1, 2, 4, 5, ..., 26 do not need downloads.
        for i in range(28):
            self.queue_dc(in_q, delays=[i if not i % 3 else None])
        in_q.put_nowait(None)

        # At 0.5 seconds
        await self.advance_to(0.5)
        # 3, 6 and 9 are running. 0 is finished
        self.assertEqual(DownloaderMock.running, 3)
        # non-downloads 1, 2, 4, 5, 7, 8 are forwarded
        self.assertEqual(out_q.qsize(), 7)
        # 9 - 26 + None are waiting to be picked up
        self.assertEqual(in_q.qsize(), 19)

        # Two downloads run in parallel. The most asymmetric way
        # to schedule the remaining downloads is:
        # 3 + 12 + 21: finished after 36 seconds
        # 6 + 15 + 24: finished after 45 seconds
        # 9 + 18 + 27: finished after 54 seconds
        for t in range(1, 36):  # until 35.5 seconds three downloads must run
            await self.advance_to(t + 0.5)
            self.assertEqual(DownloaderMock.running, 3)

        # At 54.5 seconds, the stage is done at the latest
        await self.advance_to(54.5)
        self.assertEqual(DownloaderMock.running, 0)
        self.assertEqual(DownloaderMock.downloads, 10)
        self.assertEqual(download_task.result(), DownloaderMock.downloads)
        self.assertEqual(in_q.qsize(), 0)
        self.assertEqual(out_q.qsize(), 29)

    async def test_multi_artifact_downloads(self):
        in_q = asyncio.Queue()
        out_q = asyncio.Queue()
        download_task = self.loop.create_task(self.download_task(in_q, out_q))
        self.queue_dc(in_q, delays=[])  # must be forwarded to next stage immediately
        self.queue_dc(in_q, delays=[1])
        self.queue_dc(in_q, delays=[2, 2])
        self.queue_dc(in_q, delays=[2])
        self.queue_dc(in_q, delays=[2, None])  # schedules only one download
        in_q.put_nowait(None)
        # At 0.5 seconds, three content units are downloading with four
        # downloads overall
        await self.advance_to(0.5)
        self.assertEqual(DownloaderMock.running, 4)
        self.assertEqual(out_q.qsize(), 1)
        # At 1.5 seconds, the download for the first content unit has completed.
        # At 1 second, the download of the forth content unit is started
        await self.advance_to(1.5)
        self.assertEqual(DownloaderMock.running, 4)
        self.assertEqual(out_q.qsize(), 2)
        # At 2.5 seconds, the downloads for the second and the third content unit
        # have completed
        await self.advance_to(2.5)
        self.assertEqual(DownloaderMock.running, 1)
        self.assertEqual(out_q.qsize(), 4)

        # At 3.5 seconds, stage must de done
        await self.advance_to(3.5)
        self.assertEqual(DownloaderMock.running, 0)
        self.assertEqual(DownloaderMock.downloads, 5)
        self.assertEqual(download_task.result(), DownloaderMock.downloads)
        self.assertEqual(in_q.qsize(), 0)
        self.assertEqual(out_q.qsize(), 6)

    async def test_sparse_batches_dont_block_stage(self):
        """Regression test for issue https://pulp.plan.io/issues/4018."""

        def queue_content_with_a_single_download(in_q, batchsize=100, delay=100):
            """
            Queue a batch of `batchsize` declarative_content instances. Only the
            first one triggers a download of duration `delay`.
            """
            self.queue_dc(in_q, delays=[delay])
            for i in range(batchsize - 1):
                self.queue_dc(in_q, [None])

        in_q = asyncio.Queue()
        out_q = asyncio.Queue()
        download_task = self.loop.create_task(self.download_task(in_q, out_q))

        queue_content_with_a_single_download(in_q)

        # At 0.5 seconds, the first content unit is downloading
        await self.advance_to(0.5)
        self.assertEqual(DownloaderMock.running, 1)
        self.assertEqual(out_q.qsize(), 99)

        # at 0.5 seconds next batch arrives (last batch)
        queue_content_with_a_single_download(in_q)
        in_q.put_nowait(None)

        # at 1.0 seconds, two downloads are running
        await self.advance_to(1)
        self.assertEqual(DownloaderMock.running, 2)
        self.assertEqual(out_q.qsize(), 2 * 99)

        # at 101 seconds, stage should have completed
        await self.advance_to(101)

        self.assertEqual(DownloaderMock.running, 0)
        self.assertEqual(DownloaderMock.downloads, 2)
        self.assertEqual(download_task.result(), DownloaderMock.downloads)
        self.assertEqual(in_q.qsize(), 0)
        self.assertEqual(out_q.qsize(), 201)

    async def test_cancel(self):
        in_q = asyncio.Queue()
        out_q = asyncio.Queue()
        download_task = self.loop.create_task(self.download_task(in_q, out_q))
        for i in range(4):
            self.queue_dc(in_q, delays=[100])
        in_q.put_nowait(None)

        # After 0.5 seconds, the three downloads must have started
        await self.advance_to(0.5)
        self.assertEqual(DownloaderMock.running, 3)

        download_task.cancel()

        await self.advance_to(1.0)

        with self.assertRaises(asyncio.CancelledError):
            download_task.result()
        self.assertEqual(DownloaderMock.running, 0)
        self.assertEqual(DownloaderMock.canceled, 3)
