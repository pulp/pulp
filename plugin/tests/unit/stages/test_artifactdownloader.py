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

    async def run(self):
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

    async def download_task(self, in_q, out_q,
                            max_concurrent_downloads=2, max_concurrent_content=4):
        """
        A coroutine running the downloader stage with a mocked ProgressBar.

        Returns:
            The done count of the ProgressBar.
        """
        with mock.patch('pulpcore.plugin.stages.artifact_stages.ProgressBar') as pb:
            pb.return_value.__enter__.return_value.done = 0
            ad = ArtifactDownloader(max_concurrent_downloads=max_concurrent_downloads,
                                    max_concurrent_content=max_concurrent_content)
            await ad(in_q, out_q)
        return pb.return_value.__enter__.return_value.done

    async def test_downloads(self):
        in_q = asyncio.Queue()
        out_q = asyncio.Queue()
        download_task = self.loop.create_task(self.download_task(in_q, out_q))

        # Create 12 content units, every second one must be downloaded.
        # The downloads take 1, 3, 5, 7, 9, 11 seconds; content units
        # 0, 2, ..., 10 do not need downloads.
        for i in range(12):
            self.queue_dc(in_q, delays=[i if i % 2 else None])
        in_q.put_nowait(None)

        # At 0.5 seconds
        await self.advance_to(0.5)
        # 1 and 3 are running
        # 1, 3, 5, and 7 are "in_flight"
        self.assertEqual(DownloaderMock.running, 2)
        # non-downloads 0, 2, ..., 6 forwarded
        self.assertEqual(out_q.qsize(), 4)
        # 8 - 11 + None are waiting to be picked up
        self.assertEqual(in_q.qsize(), 5)

        # Two downloads run in parallel. The most asymmetric way
        # to schedule the remaining downloads is:
        # 1 + 5 + 7: finished after 13 seconds
        # 3 + 9 + 11: finished after 23 seconds
        for t in range(1, 13):  # until 12.5 seconds two downloads must run
            await self.advance_to(t + 0.5)
            self.assertEqual(DownloaderMock.running, 2)

        # At 23.5 seconds, the stage is done at the latest
        await self.advance_to(23.5)
        self.assertEqual(DownloaderMock.running, 0)
        self.assertEqual(DownloaderMock.downloads, 6)
        self.assertEqual(download_task.result(), DownloaderMock.downloads)
        self.assertEqual(in_q.qsize(), 0)
        self.assertEqual(out_q.qsize(), 13)

    async def test_multi_artifact_downloads(self):
        in_q = asyncio.Queue()
        out_q = asyncio.Queue()
        download_task = self.loop.create_task(self.download_task(in_q, out_q))
        self.queue_dc(in_q, delays=[])  # must be forwarded to next stage immediately
        self.queue_dc(in_q, delays=[1])
        self.queue_dc(in_q, delays=[2, 2])
        self.queue_dc(in_q, delays=[2, None])  # schedules only one download
        in_q.put_nowait(None)
        # At 0.5 seconds, two content units are downloading with two
        # downloads overall
        await self.advance_to(0.5)
        self.assertEqual(DownloaderMock.running, 2)
        self.assertEqual(out_q.qsize(), 1)
        # At 1.5 seconds, the download for the first content unit has completed
        await self.advance_to(1.5)
        self.assertEqual(DownloaderMock.running, 2)
        self.assertEqual(out_q.qsize(), 2)
        # At 2.5 seconds, the first download for the second content unit has
        # completed. At 1 second, either the second download of the second content unit, or the
        # first download of the third unit is started
        await self.advance_to(2.5)
        self.assertEqual(DownloaderMock.running, 2)
        self.assertEqual(out_q.qsize(), 2)
        # At 3.5 seconds, only one of the artifacts is left
        await self.advance_to(3.5)
        self.assertEqual(DownloaderMock.running, 1)
        self.assertEqual(out_q.qsize(), 3)

        # At 4.5 seconds, stage must de done
        await self.advance_to(4.5)
        self.assertEqual(DownloaderMock.running, 0)
        self.assertEqual(DownloaderMock.downloads, 4)
        self.assertEqual(download_task.result(), DownloaderMock.downloads)
        self.assertEqual(in_q.qsize(), 0)
        self.assertEqual(out_q.qsize(), 5)

    async def test_download_stall(self):
        in_q = asyncio.Queue()
        out_q = asyncio.Queue()
        download_task = self.loop.create_task(self.download_task(in_q, out_q))

        self.queue_dc(in_q, delays=[1, 1])
        self.queue_dc(in_q, delays=[1, 1])

        # At 0.5 seconds, the first content unit is downloading with two
        # downloads overall
        await self.advance_to(0.5)
        self.assertEqual(DownloaderMock.running, 2)

        # At 1.5 seconds, the downloads for the second content are running
        await self.advance_to(1.5)
        self.assertEqual(DownloaderMock.running, 2)
        self.assertEqual(out_q.qsize(), 1)

        # At 2.5 second all content units are completed and the stage is waiting
        # for input
        await self.advance_to(2.5)
        self.assertEqual(DownloaderMock.running, 0)
        self.assertEqual(out_q.qsize(), 2)

        # A new content unit arrives
        self.queue_dc(in_q, delays=[1, 1])

        # At 3 seconds, download must be running for it
        await self.advance_to(3)
        self.assertEqual(DownloaderMock.running, 2)
        self.assertEqual(out_q.qsize(), 2)

        # Upstream stage completes
        in_q.put_nowait(None)

        await self.advance_to(4)

        self.assertEqual(DownloaderMock.running, 0)
        self.assertEqual(DownloaderMock.downloads, 6)
        self.assertEqual(download_task.result(), DownloaderMock.downloads)
        self.assertEqual(in_q.qsize(), 0)
        self.assertEqual(out_q.qsize(), 4)

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

        # After 0.5 seconds, the first two downloads must have started
        await self.advance_to(0.5)
        self.assertEqual(DownloaderMock.running, 2)

        download_task.cancel()

        await self.advance_to(1.0)

        with self.assertRaises(asyncio.CancelledError):
            download_task.result()
        self.assertEqual(DownloaderMock.running, 0)
        self.assertEqual(DownloaderMock.canceled, 2)
