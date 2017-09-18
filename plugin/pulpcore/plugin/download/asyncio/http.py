from .base import attach_url_to_exception, BaseDownloader, DownloadResult


class HttpDownloader(BaseDownloader):
    """
    An asyncio aware HTTP/HTTPS Downloader built on aiohttp.

    This is the default downloader used by the DownloaderFactory and GroupDownloader. It is designed
    to be easily subclassed for customizable download behaviors. If a user subclasses this, they can
    specify the subclass to be used with either the DownloaderFactory or GroupDownloader.

    Each downloader downloads data from one `url` and are not reused. Each downloader requires an
    `aiohttp.ClientSession` for it to use. The aiohttp.ClientSession provides connection pooling,
    connection reusage, and keep-alives. Don't create one session per Downloader, use one session
    shared by all of your downloaders.

    `aiohttp.ClientSession` objects also accept options which will then apply to all downloads which
    use them. These things include auth, timeouts, headers, etc. For more info on these options see
    the `aiohttp.ClientSession` docs for more information:
    http://aiohttp.readthedocs.io/en/stable/client_reference.html#aiohttp.ClientSession

    The `aiohttp.ClientSession` can additionally be configured for SSL configuration by passing in a
    `aiohttp.TCPConnector`. For information on configuring either server or client certificate based
    identity verification, see the aiohttp documentation:
    http://aiohttp.readthedocs.io/en/stable/client.html#ssl-control-for-tcp-sockets

    For more information on `aiohttp.BasicAuth` objects, see their docs:
    http://aiohttp.readthedocs.io/en/stable/client_reference.html#aiohttp.BasicAuth

    Usage:
        >>> session = aiohttp.ClientSession()
        >>> downloader_obj = HttpDownloader(session, url)
        >>> downloader_coroutine = downloader_obj.run()
        >>> loop = asyncio._get_running_loop()
        >>> done, not_done = loop.run_until_complete(asyncio.wait([downloader_coroutine]))
        >>> for task in done:
        >>>     result = task.result()  # This is a DownloadResult

    Attributes:
        session (aiohttp.ClientSession): The session to be used by the downloader.
        auth (aiohttp.BasicAuth): An object that represents HTTP Basic Authorization (optional)
        proxy (str): An optional proxy URL.
        proxy_auth (aiohttp.BasicAuth): An optional object that represents proxy HTTP Basic
            Authorization.
        headers_ready_callback (callable): An optional callback that accepts a single dictionary
            as its argument. The callback will be called when the response headers are
            available. The dictionary passed has the header names as the keys and header values
            as its values. e.g. `{'Transfer-Encoding': 'chunked'}`

    This downloader also has all of the attributes of
    :class:`~pulpcore.plugin.download.asyncio.BaseDownloader`
    """

    def __init__(self, session, url, auth=None, proxy=None, proxy_auth=None,
                 headers_ready_callback=None, **kwargs):
        """
        Args:
            url (str): The url to download.
            session (aiohttp.ClientSession): The session to be used by the downloader.
            auth (aiohttp.BasicAuth): An object that represents HTTP Basic Authorization (optional)
            proxy (str): An optional proxy URL.
            proxy_auth (aiohttp.BasicAuth): An optional object that represents proxy HTTP Basic
                Authorization.
            headers_ready_callback (callable): An optional callback that accepts a single dictionary
                as its argument. The callback will be called when the response headers are
                available. The dictionary passed has the header names as the keys and header values
                as its values. e.g. `{'Transfer-Encoding': 'chunked'}`
            kwargs (dict): This accepts the parameters of
                :class:`~pulpcore.plugin.download.asyncio.BaseDownloader`.
        """
        self.session = session
        self.auth = auth
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.headers_ready_callback = headers_ready_callback
        super().__init__(url, **kwargs)

    async def _handle_response(self, response):
        """
        Handle the aiohttp response by writing it to disk and calculating digests

        Args:
            response (aiohttp.ClientResponse): The response to handle.

        Returns:
             DownloadResult: Contains information about the result. See the DownloadResult docs for
                 more information.
        """
        if self.headers_ready_callback:
            self.headers_ready_callback(response.headers)
        while True:
            chunk = await response.content.read(1024)
            if not chunk:
                self.validate_size()
                self.validate_digests()
                break  # the download is done
            self.handle_data(chunk)
        return DownloadResult(path=self.path, artifact_attributes=self.artifact_attributes,
                              url=self.url, exception=None)

    @attach_url_to_exception
    async def run(self):
        """
        Download, validate, and compute digests on the `url`. This is a coroutine.

        This method provides the same return object type and documented in
        :meth:`~pulpcore.plugin.download.asyncio.BaseDownloader.run`.
        """
        async with self.session.get(self.url) as response:
            response.raise_for_status()
            to_return = await self._handle_response(response)
            await response.release()
        return to_return
