import os
import errno

from http import HTTPStatus
from requests import Session
from requests.adapters import HTTPAdapter, Retry, Response
from threading import RLock


from .request import Request


class LocalAdapter(HTTPAdapter):
    """
    Handle `file://` URLs.
    """

    def send(self, request, **unused):
        """
        Send the request.

        Args:
            request: The request to send.
            unused: Unused.

        Returns:
            A 200 response.

        Raises:
            Anything raised when opening the file.

        """
        path = request.url[7:]
        response = Response()
        response.raw = open(path, 'rb')
        response.url = request.url
        response.status_code = 200
        return response

    def close(self):
        """
        Close the handler.
        """
        pass


class HttpRequest(Request):
    """
    An HTTP request.

    Attributes:
        ssl_ca_certificate (str): An optional absolute path to an PEM encoded CA certificate.
        ssl_client_certificate (str): An optional absolute path to an PEM encoded
            client certificate.
        ssl_client_key (str): An optional absolute path to an PEM encoded
            client private key.
        user (str): An optional username for basic authentication.
        password (str): An optional password used for basic authentication.
        proxy_url (str): An optional proxy URL.
        headers (dict): Optional HTTP headers.
        http_code (int): The HTTP status code returned by the server.

    Examples:
        >>>
        >>> from pulp.download import HttpRequest
        >>>
        >>> url = ...
        >>> destination = ...
        >>> request = HttpRequest(url, destination)
        >>> request()
        >>> # Go read the downloaded file \o/
        >>>

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

    def __init__(self, url, destination):
        """
        Args:
            url (str): A file download URL.
            destination (str): An absolute path to where the downloaded file is stored.

        """
        super(HttpRequest, self).__init__(url, destination)
        self.ssl_ca_certificate = None
        self.ssl_client_certificate = None
        self.ssl_client_key = None
        self.user = None
        self.password = None
        self.proxy_url = None
        self.headers = None
        self.http_code = 0
        self._mutex = RLock()

    @property
    def session(self):
        """
        The `requests` session.

        Returns:
            Session: The shared or newly created session.

        Notes:
            The session can be shared between request but this needs to be
            facilitated by a 3rd object by setting the `shared` dictionary
            to be the same.

        """
        key = 'session'
        with self._mutex:
            try:
                return self.scratchpad[key]
            except KeyError:
                session = self.create_session()
                self.scratchpad[key] = session
                return session

    def create_directory(self):
        """
        Create the directory as needed.

        Raises:
            OSError: When the directory cannot be created.
        """
        try:
            os.makedirs(os.path.dirname(self.destination))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def store_content(self, result):
        """
        Read the input stream and write the file content to the destination.

        Args:
            result: The `requests` result.

        Raises:
            OSError: When the file cannot be opened/created.
            IOError: When the file cannot be written.

        """
        n_bytes = 0x100000  # 1mb
        with open(self.destination, 'w+') as fp:
            for bfr in result.iter_content(chunk_size=n_bytes):
                fp.write(str(bfr))

    def on_succeeded(self, result):
        """
        Handle a successful download result.
        The destination is created and the file written to the `destination`.

        Args:
            result: The `requests` result.

        Raises:
            OSError: When the directory cannot be created.
            IOError: When the file cannot be written.

        """
        super(HttpRequest, self).on_succeeded(result)
        self.create_directory()
        self.store_content(result)

    def failed(self):
        """
        Get whether the request has failed.

        Returns:
            bool: True when http_code is not 200.

        """
        return self.http_code != HTTPStatus.OK

    def __call__(self):
        """
        Send the HTTP request using the `requests` session.

        """
        result = self.session.get(self.url)
        self.http_code = result.status_code
        if self.succeeded():
            self.on_succeeded(result)
        else:
            self.on_failed(result)

    def __str__(self):
        # Testing
        return str(self.__dict__)
