from gettext import gettext as _
from logging import getLogger
from threading import RLock


from .delegation import delegate
from .validation import ValidationError
from .writer import FileWriter, TextWriter


log = getLogger(__name__)


class DownloadFailed(Exception):
    """
    Download failed.

    Attributes:
        download (Download): The failed download.
        reason (str): The reason it failed.
    """

    def __init__(self, download, reason=''):
        """
        Args:
            download (Download): The failed download.
            reason (str): The reason it failed.
        """
        self.download = download
        self.reason = reason

    def __str__(self):
        return _('{r} - Failed. Reason: {d}'.format(r=self.download, d=self.reason))


class Download:
    """
    An ABSTRACT download object.
    Represents a unit of work to download a file. A download is a
    command-pattern object.

    Attributes:
        url (str): A file download URL.
        writer (path): The storage path for the downloaded file.
        retries (int): Total number of retries possible.
        context (Context): The download context.
        delegate (Delegate): Download delegate.
        attachment: Arbitrary object attached to the download.
        reply: The remote server reply.
        # options
        ssl_ca_certificate (str): An optional absolute path to an PEM encoded CA certificate.
        ssl_client_certificate (str): An optional absolute path to an PEM encoded
            client certificate.
        ssl_client_key (str): An optional absolute path to an PEM encoded
            client private key.
        ssl_validation (bool): Validate the server SSL certificate.
        user (str): An optional username for basic authentication.
        password (str): An optional password used for basic authentication.
        connect_timeout (int): Connection timeout in seconds.
        read_timeout (int): Read timeout in seconds.

    Notes:
        The validation is applied in order listed.
    """

    # Data transfer buffer size in bytes.
    BLOCK = 102400

    def __init__(self, url, path=None):
        """
        Args:
            url (str): A file download URL.
            path (str): The storage path for the downloaded file.
        """
        super(Download, self).__init__()
        self.url = url
        if path:
            self.writer = FileWriter(path)
        else:
            self.writer = TextWriter()
        self.retries = 1
        self.context = Context()
        self.delegate = None
        self.attachment = None
        self.reply = None
        # options
        self.ssl_ca_certificate = None
        self.ssl_client_certificate = None
        self.ssl_client_key = None
        self.ssl_validation = True
        self.user = None
        self.password = None
        self.connect_timeout = 10
        self.read_timeout = 30

    @property
    def path(self):
        """
        The storage path for the downloaded file.

        Returns:
            str: The absolute path.
        """
        return self.writer.path

    @property
    def validations(self):
        """
        The collection of validations applied to the downloaded file.

        Returns:
            list: of validations.
        """
        return self.writer.validations

    @delegate
    def prepare(self):
        """
        Prepare to be executed.
        """
        pass

    @delegate
    def validate(self):
        """
        Apply validations.

        Raises:
            ValidationError: On validation failed.
        """
        for validation in self.validations:
            log.debug(
                _('Apply validation: %(validator)s'),
                {
                    'validator': validation
                })
            try:
                validation.apply()
            except ValidationError as error:
                log.info(_('Validation failed: %(error)s'), {'error': error})
                raise error
            except Exception as unexpected:
                log.exception(unexpected)
                raise unexpected

    @delegate
    def on_reply(self):
        """
        Handle the remote server reply.
        """
        pass

    @delegate
    def on_succeeded(self):
        """
        Handle a successful download result.

        Raises:
            ValidationError: On validation failed.
        """
        self.validate()

    @delegate
    def on_failed(self):
        """
        The download has failed.
        """
        pass

    @delegate
    def on_error(self):
        """
        The download has encountered an error.

        Returns:
            (bool): True if repaired and may be retried.
        """
        return False

    def _repair(self, error):
        """
        The download has encountered an error.
        Attempt to repair and retry using `on_error()` depending on remaining
        available retries.

        Args:
            error (DownloadFailed): The raised exception.

        Raises:
            DownloadFailed: The download failed and could not be repaired.
        """
        try:
            repaired = False
            while self.retries:
                self.retries -= 1
                repaired = self.on_error()
                if repaired:
                    try:
                        self._try()
                        break
                    except DownloadFailed as rf:
                        repaired = False
                        error = rf
                else:
                    break
            if not repaired:
                self.on_failed()
                raise error
        except Exception:
            log.exception(_('Repair failed.'))
            raise error

    def _try(self):
        """
        Try to download.
        """
        with self.writer:
            self._send()
            self.on_reply()
        self.on_succeeded()

    def __call__(self):
        """
        Execute the download.
         - _send()

        Raises:
            DownloadFailed: The download failed and could not be repaired.
        """
        try:
            self.prepare()
            self._try()
        except DownloadFailed as error:
            self._repair(error)

    def _send(self):
        """
        Send the download.
        This is the *main* method responsible for implementing the actual
        download by sending a protocol specific download. The reply
        is handled by on_reply(), on_succeeded() and on_error().

        Raises:
            DownloadFailed: The download failed and could not be repaired.

        Notes:
            Must be implemented by subclass.
        """
        raise NotImplementedError()

    def __str__(self):
        _id = str(id(self))[-4:]
        description = _(
            '{t}: id={s} url={u} path={p}'
            ' | repair: retries={r}'
            ' | timeout: connect={tc} read={tr}'
            ' | auth: user={U} password={P}'
            ' | ssl: validation={v} CA={a} key={k} certificate={c}')
        return description.format(
            t=type(self).__name__,
            s=_id,
            u=self.url,
            p=self.path,
            r=self.retries,
            tc=self.connect_timeout,
            tr=self.read_timeout,
            U=self.user,
            P=self.password,
            v=self.ssl_validation,
            a=self.ssl_ca_certificate,
            k=self.ssl_client_key,
            c=self.ssl_ca_certificate)


class Context:
    """
    A download context.

    Attributes:
        properties (dict): Arbitrary properties.
        _mutex (RLock): The object mutex.

    Examples:
        >>>
        >>> def get_token(self):
        >>>     with self.context as context:
        >>>         try:
        >>>             return context.token
        >>>         except KeyError:
        >>>             token = self.generate_token()
        >>>             context.token = token
        >>>             return token
        >>>
    """

    def __init__(self, **properties):
        """
        Args:
            **properties (dict): Initial properties.
        """
        self.__dict__.update(properties)
        self.__dict__['MUTEX'] = RLock()

    @property
    def _mutex(self):
        return self.__dict__['MUTEX']

    def __setattr__(self, key, value):
        with self._mutex:
            super(Context, self).__setattr__(key, value)

    def __enter__(self):
        self._mutex.acquire()
        return self

    def __exit__(self, *unused):
        self._mutex.release()
