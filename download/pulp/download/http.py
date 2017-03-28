import errno

from gettext import gettext as _
from logging import getLogger
from http import HTTPStatus
from requests import Session
from requests.adapters import HTTPAdapter, Retry, Response
from requests.exceptions import SSLError


from .single import Download, DownloadFailed


log = getLogger(__name__)


class HttpFailed(DownloadFailed):
    """
    Download failed.

    Attributes:
        download (Download): The failed download.
        status (int): The status (code) in the server reply.
    """

    def __init__(self, download, status):
        """
        Args:
            download (Download): The failed download.
            status (int): The status (code) in the server reply.
        """
        super(HttpFailed, self).__init__(download, 'HTTP [{}]'.format(status))
        self.status = status


class LocalAdapter(HTTPAdapter):
    """
    Handle `file://` URLs.
    """

    STATUS = {
        errno.ENOENT: int(HTTPStatus.NOT_FOUND),
        errno.EPERM:  int(HTTPStatus.FORBIDDEN),
    }

    def send(self, download, **unused):
        """
        Send the download.

        Args:
            download: The download to send.
            unused: Unused.

        Returns:
            Response: Always.
        """
        response = Response()
        response.url = download.url
        try:
            path = download.url[7:]
            response.raw = open(path, 'rb')
            response.status_code = HTTPStatus.OK
        except IOError as e:
            status = self.STATUS.get(e.errno, int(HTTPStatus.INTERNAL_SERVER_ERROR))
            response.status_code = status
        return response

    def close(self):
        """
        Close the handler.
        """
        pass


class HttpDownload(Download):
    """
    An HTTP download.

    Attributes:
        proxy_url (str): An optional proxy URL.
        headers (dict): The optional HTTP headers.

    Examples:
        >>>
        >>> from pulp.download import HttpDownload
        >>>
        >>> url = ...
        >>> path = ...
        >>> download = HttpDownload(url, path)
        >>> download()
        >>> # Go read the downloaded file \o/
        >>>

    Notes:
        The 'session' may be shared through the context.session.
    """

    @staticmethod
    def create_session():
        """
        Create a session.

        Returns:
            Session: The created session.

        """
        session = Session()
        adapter = HTTPAdapter(max_retries=Retry())
        session.mount('file://', LocalAdapter())
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def __init__(self, url, path=None, method='GET'):
        """
        Args:
            url (str): A file download URL.
            path (str): The storage path for the downloaded file.
        """
        super(HttpDownload, self).__init__(url, path)
        self.method = self._find_method(method)
        self.proxy_url = None
        self.headers = None

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
        The `downloads` session.

        Returns:
            Session: The shared or newly created session.

        Notes:
            The session can be shared between download but this needs to be
            facilitated by a 3rd object by setting the `shared` dictionary
            to be the same.
        """
        with self.context as context:
            try:
                return context.session
            except AttributeError:
                session = self.create_session()
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
            'GET': self.get,
            'HEAD': self.head,
        }
        try:
            return methods[name.upper()]
        except KeyError:
            _list = '|'.join(sorted(methods.keys()))
            msg = _('method must be: ({list})'.format(list=_list))
            raise ValueError(msg)

    @property
    def options(self):
        """
        Get `downloads` keyword options based on attributes.

        Returns:
            dict: The options.
        """
        options = {
            'stream': True,
            'timeout': (self.connect_timeout, self.read_timeout)
        }

        # Basic Auth
        if self.user:
            options['auth'] = (self.user, self.password)

        # Proxy
        if self.proxy_url:
            options['proxies'] = {
                'http': self.proxy_url,
                'https': self.proxy_url,
                'ftp': self.proxy_url,
            }

        # Headers
        if self.headers:
            options['headers'] = self.headers

        # SSL validation
        if self.ssl_ca_certificate:
            options['verify'] = self.ssl_ca_certificate

        # SSL client certificate
        if self.ssl_client_certificate:
            options['cert'] = self.ssl_client_certificate

        # SSL client key
        if self.ssl_client_key:
            options['cert'] = (options['cert'], self.ssl_client_key)

        return options

    def get(self):
        """
        Send the HTTP `GET` download.

        Returns:
            download.Response

        Raises:
            SSLError: On SSL error.
        """
        return self.session.get(self.url, **self.options)

    def head(self):
        """
        Send the HTTP `HEAD` download.

        Returns:
            download.Response

        Raises:
            SSLError: On SSL error.
        """
        return self.session.head(self.url, **self.options)

    def _send(self):
        """
        Send the HTTP download request.

        Raises:
            HttpFailed: The download failed and could not be repaired.
        """
        try:
            self.reply = self.method()
            if self.status != HTTPStatus.OK:
                raise HttpFailed(self, self.status)
            for bfr in self.reply.iter_content(chunk_size=self.BLOCK):
                self.writer.append(bfr)
        except SSLError:
            raise HttpFailed(self, int(HTTPStatus.UNAUTHORIZED))

    def __str__(self):
        base = super(HttpDownload, self).__str__()
        description = _('{b} | http: status={s} proxy={P} headers={h}')
        return description.format(
            b=base,
            s=self.status,
            P=self.proxy_url,
            h=self.headers)
