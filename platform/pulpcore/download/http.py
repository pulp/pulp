from gettext import gettext as _
from logging import getLogger
from http import HTTPStatus
from requests import Session
from requests.exceptions import SSLError

from .error import DownloadFailed, NotAuthorized, NotFound
from .single import Download

from .settings import Timeout, SSL, User


log = getLogger(__name__)


# HTTP codes mapped to standard exceptions.
ERROR = {
    HTTPStatus.NOT_FOUND: NotFound,
    HTTPStatus.UNAUTHORIZED: NotAuthorized
}


class HttpDownload(Download):
    """
    An HTTP/HTTPS download.

    Attributes:
        timeout (pulpcore.download.Timeout): Timeout settings.
        user (pulpcore.download.User): User settings for basic-authentication.
        ssl (pulpcore.download.SSL): SSL/TLS settings.
        proxy_url (str): An optional proxy URL.
        headers (dict): The optional HTTP headers.

    Examples:
        >>>
        >>> from pulpcore.download import DownloadError, HttpDownload, FileWriter
        >>>
        >>> url = 'http://..'
        >>> path = ...
        >>>
        >>> download = HttpDownload(url, FileWriter(path))
        >>>
        >>> try:
        >>>     download()
        >>> except DownloadError:
        >>>     # An error occurred.
        >>> else:
        >>>     # Go read the downloaded file \o/
        >>>
        >>> # OR
        >>>
        >>> download = HttpDownload(
        >>>     url=url,
        >>>     writer=FileWriter(path),
        >>>     timeout=Timeout(connect=10, read=15),
        >>>     user=User(name='elmer', password='...'),
        >>>     ssl=SSL(
        >>>         ca_certificate='path-to-certificate',
        >>>         client_certificate='path-to-certificate',
        >>>         client_key='path-to-key',
        >>>         validation=True),
        >>>     proxy_url='http://user:password@gateway.org')
        >>>
        >>> try:
        >>>     download()
        >>> except DownloadError:
        >>>     # An error occurred.
        >>> else:
        >>>     # Go read the downloaded file \o/
        >>>
        >>> # OR
        >>>
        >>> download = HttpDownload(url, FileWriter(path))
        >>> # optional settings
        >>> download.timeout.connect = 10
        >>> download.timeout.read = 30
        >>> download.user.name = 'elmer'
        >>> download.user.password = '...'
        >>> download.ssl.ca_certificate='path-to-certificate',
        >>> download.ssl.client_certificate='path-to-certificate',
        >>> download.ssl.client_key='path-to-key',
        >>> download.ssl.validation=True),
        >>> download.proxy_url='http://user:password@gateway.org'))
        >>>
        >>> try:
        >>>     download()
        >>> except DownloadError:
        >>>     # An error occurred.
        >>> else:
        >>>     # Go read the downloaded file \o/
        >>>

    Notes:
        The 'session' may be shared through the context.session.
    """

    __slots__ = (
        'timeout',
        'user',
        'ssl',
        'proxy_url',
        'headers',
        'method'
    )

    def __init__(self,
                 url,
                 writer,
                 method='GET',
                 timeout=None,
                 user=None,
                 ssl=None,
                 proxy_url=None,
                 headers=None):
        """
        Args:
            url (str): A file download URL.
            writer (Writer): An object used to store downloaded file.
            method (str): The HTTP method (GET|HEAD).
            timeout (pulpcore.download.Timeout): Timeout settings.
            user (pulpcore.download.User): User settings for basic-authentication.
            ssl (pulpcore.download.SSL): SSL/TLS settings.
            proxy_url (str): An optional proxy URL.
            headers (dict): The optional HTTP headers.
        """
        super(HttpDownload, self).__init__(url, writer)
        self.timeout = timeout or Timeout()
        self.user = user or User()
        self.ssl = ssl or SSL()
        self.proxy_url = proxy_url
        self.headers = headers or {}
        self.method = self._find_method(method)

    @property
    def status(self):
        """
        The status code in the reply.

        Returns:
            (int): The reply status.

        """
        try:
            return self.reply.status_code
        except AttributeError:
            return 0

    @property
    def session(self):
        """
        The `requests` session.

        Returns:
            Session: The shared or newly created session.

        Notes:
            The session can be shared between download but this needs to be
            facilitated by a 3rd object by setting the `context` to be the same.
        """
        with self.context as context:
            try:
                return context.session
            except AttributeError:
                session = Session()
                context.session = session
                return session

    def _find_method(self, name):
        """
        Find an http method by name.

        Args:
            name: The method name.  see: METHODS.

        Returns:
            instancemethod: When matched.

        Raises:
            ValueError: When not matched.
        """
        methods = {
            'GET': self._get,
            'HEAD': self._head,
        }
        try:
            return methods[name.upper()]
        except KeyError:
            _list = '|'.join(sorted(methods.keys()))
            msg = _('method must be: ({list})'.format(list=_list))
            raise ValueError(msg)

    def _settings(self):
        """
        Get `requests` keyword options based on attributes.

        Returns:
            dict: The options.
        """
        options = {
            'stream': True,
            'timeout': (self.timeout.connect, self.timeout.read)
        }
        if self.user.name:
            options['auth'] = (self.user.name, self.user.password)
        if self.proxy_url:
            options['proxies'] = {
                'http': self.proxy_url,
                'https': self.proxy_url,
            }
        if self.headers:
            options['headers'] = self.headers
        if self.ssl.ca_certificate:
            options['verify'] = self.ssl.ca_certificate
        if self.ssl.client_certificate:
            options['cert'] = self.ssl.client_certificate
        if self.ssl.client_key:
            options['cert'] = (options['cert'], self.ssl.client_key)

        return options

    def _get(self):
        """
        Send the HTTP `GET` download.

        Returns:
            download.Response

        Raises:
            SSLError: On SSL error.
        """
        return self.session.get(self.url, **self._settings())

    def _head(self):
        """
        Send the HTTP `HEAD` download.

        Returns:
            download.Response

        Raises:
            SSLError: On SSL error.
        """
        return self.session.head(self.url, **self._settings())

    def _send(self):
        """
        Send the HTTP download request.

        Raises:
            DownloadFailed: The download failed and could not be repaired.
        """
        try:
            self.reply = self.method()
            if self.status != HTTPStatus.OK:
                reason = _('HTTP [{n}]').format(n=self.status)
                raise ERROR.get(self.status, DownloadFailed)(self, reason)
            for buffer in self.reply.iter_content(chunk_size=self.BLOCK):
                self._write(buffer)
        except OSError as error:
            # Cannot read certificate.
            raise DownloadFailed(self, str(error))
        except SSLError as error:
            # SSL handshake failed.
            raise NotAuthorized(self, str(error))

    def __str__(self):
        base = super(HttpDownload, self).__str__()
        http = _('proxy={p} headers={h}').format(
            p=self.proxy_url,
            h=self.headers)
        return ' | '.join([
            base,
            str(self.timeout),
            str(self.ssl),
            str(self.user),
            http,
        ])
