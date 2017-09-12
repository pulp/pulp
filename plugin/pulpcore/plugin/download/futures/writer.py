import os
import errno

from io import BytesIO
from logging import getLogger


log = getLogger(__name__)


class Writer:
    """
    Downloaded content writer.

    Attributes:
        fp: An open file-like object used for writing.
    """

    __slots__ = ('fp',)

    def __init__(self, fp=None):
        """
        Args:
            fp: An open file-like object used for writing.
        """
        self.fp = fp

    @property
    def is_open(self):
        """
        Get whether the writer is open.

        Returns:
            bool: True when open.
        """
        return (self.fp is not None) and (not self.fp.closed)

    def open(self):
        """
        Open for writing.
        The directory tree is created as necessary.
        """
        pass

    def append(self, buffer):
        """
        Append (write) the buffer.

        Args:
            buffer (bytes): A buffer to append.

        Returns:
            int: The number of bytes appended.
        """
        return self.fp.write(buffer)

    def close(self):
        """
        Close the target file.
        """
        pass

    def discard(self):
        """
        Discard written content.
        """
        pass

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *unused):
        self.close()


class FileWriter(Writer):
    """
    Downloaded content writer.
    Write content to a file.

    Attributes:
        path (str): The absolute path to the file. May be None.
    """

    __slots__ = ('path',)

    def __init__(self, path):
        """
        Args:
            path (str): The absolute path to the file. May be None.
        """
        super(FileWriter, self).__init__()
        self.path = path

    def open(self):
        """
        Open for writing.
        The directory tree is created as necessary.
        """
        if self.is_open:
            return
        self._mkdir()
        self.fp = open(self.path, 'wb')

    def close(self):
        """
        Close the target file.
        """
        if not self.is_open:
            return
        try:
            self.fp.close()
        except Exception:
            log.exception(self)
        finally:
            self.fp = None

    def discard(self):
        """
        Discard written content.
        """
        os.unlink(self.path)

    def _mkdir(self):
        """
        Create the directory as needed.

        Raises:
            OSError: When the directory cannot be created.
        """
        _dir = os.path.dirname(self.path)
        if not _dir:
            return
        try:
            os.makedirs(_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def __str__(self):
        return self.path


class BufferWriter(Writer):
    """
    Buffer writer.
    Used to store downloaded file content into a buffer.
    """

    def open(self):
        """
        Create the buffer.
        """
        self.fp = BytesIO()

    def content(self):
        """
        Get the buffered content.

        Returns:
            str: The buffered content.
        """
        self.fp.seek(0)
        return self.fp.read().decode('utf8', 'replace')

    def __str__(self):
        return 'buffer'
