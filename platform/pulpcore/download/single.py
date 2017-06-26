from gettext import gettext as _
from logging import getLogger
from threading import RLock


from .delegation import delegate
from .error import DownloadFailed
from .validation import ValidationError


log = getLogger(__name__)


class Download:
    """
    An ABSTRACT download object.
    Represents a unit of work to download a file. A download is a
    command-pattern object.

    Attributes:
        url (str): A file download URL.
        writer (Writer): An object used to store downloaded file.
        validations (list): Collection of Validations to be applied.
        context (Context): The download context.
        retries (int): The total number of retries possible.
        delegate (Delegate): A download delegate.
        attachment: Arbitrary object attached to the download.
        reply: The remote server reply.

    Any method decorated with `@delegate` may be forwarded to the `delegate` for
    implementation.  The delegate must define a public method with the same name
    (without the `_` prefix).  For example, for `_on_error()`, the delegate would
    define a method named `on_error(self, download, error)`.  Note: The `download`
    is injected (passed) as the first argument.

    Notes:
        The validations are applied in order listed.
        Settings may be shared between downloads.
    """

    # Data transfer buffer size in bytes.
    BLOCK = 102400
    # Number of retires on failed download.
    RETRIES = 1

    __slots__ = (
        'url',
        'writer',
        'validations',
        'context',
        'retries',
        'delegate',
        'attachment',
        'reply'
    )

    def __init__(self, url, writer):
        """
        Args:
            url (str): A file download URL.
            writer (Writer): An object used to store downloaded file.
        """
        super(Download, self).__init__()
        self.url = url
        self.writer = writer
        self.validations = []
        self.context = Context()
        self.retries = Download.RETRIES
        self.delegate = None
        self.attachment = None
        self.reply = None

    def _prepare(self):
        """
        Prepare to be executed.
        """
        log.debug(_('Prepare: %(d)s'), {'d': self})
        self._on_prepare()

    def _send(self):
        """
        Send the download.
        This is the *main* method responsible for implementing the actual
        download by sending a protocol specific download.

        Raises:
            DownloadFailed: The download failed and could not be repaired.

        Notes:
            Must be implemented by subclass.
        """
        raise NotImplementedError()

    def _repair(self, error):
        """
        The download has encountered an error.
        Attempt to repair and retry using `_on_error()` depending on remaining
        available retries.

        Args:
            error (DownloadFailed): The raised exception.

        Raises:
            DownloadFailed: The download failed and could not be repaired.
        """
        log.debug(_('Repair: %(d)s'), {'d': self})
        try:
            retries = self.retries
            while retries:
                retries -= 1
                repaired = self._on_error(error)
                if not repaired:
                    break
                try:
                    self._attempt()
                except DownloadFailed:
                    continue
                else:
                    return
            if not retries:
                self._on_failed()
                raise error
        except Exception:
            log.exception(_('Repair failed: {d}').format(d=self))
            self._on_failed()
            raise error

    def _write(self, bfr):
        """
        Write downloaded content.

        Args:
            bfr (bytes): A buffer to append.
        """
        self.writer.append(bfr)
        for validation in self.validations:
            validation.update(bfr)

    def _attempt(self):
        """
        Attempt to download.

        Raises:
            DownloadFailed: The download failed.
            ValidationError: On validation failed.
        """
        log.debug(_('Attempt: %(d)s'), {'d': self})
        with self.writer:
            self._send()
            self._on_reply()
        self._on_succeeded()
        self._validate()

    def _validate(self):
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
    def _on_prepare(self):
        """
        Prepared to be executed.
        """
        pass

    @delegate
    def _on_reply(self):
        """
        A reply has been received.
        """
        pass

    @delegate
    def _on_succeeded(self):
        """
        The download has succeeded.
        """
        pass

    @delegate
    def _on_failed(self):
        """
        The download has failed.
        All efforts to repair and retry have failed.
        """
        pass

    @delegate
    def _on_error(self, error):
        """
        The download has encountered an error.
        This provides the (optional) delegate an opportunity to repair
        and try the download.

        Args:
            error (DownloadFailed): The raised exception.

        Returns:
            (bool): True if repaired and may be retried.
        """
        return False

    def __call__(self):
        """
        Execute the download.

        Raises:
            DownloadFailed: The download failed and could not be repaired.
            ValidationError: On validation failed.
        """
        try:
            self._prepare()
            self._attempt()
        except DownloadFailed as error:
            self._repair(error)

    def __str__(self):
        _id = str(id(self))[-4:]
        description = _(
            '{t}: id={id} url={u} writer={w}'
            ' | repair: retries={r}')
        return description.format(
            t=type(self).__name__,
            id=_id,
            u=self.url,
            w=self.writer,
            r=self.retries)


class Context:
    """
    A download context.
    Each download has a reference to a context used to safely share resources
    such as HTTP sessions and authentication tokens.

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
            properties (dict): Initial properties.
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
