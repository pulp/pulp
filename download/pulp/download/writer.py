import os
import errno

from io import BytesIO
from logging import getLogger


log = getLogger(__name__)


class Writer:
    """
    Downloaded content writer.

    Attributes:
        path (str): The absolute path to the file. May be None.
        validations (list): Collection of Validations to be applied.
        fp: An open file-like object used for writing.
    """

    def __init__(self, path=None, fp=None):
        """
        Attributes:
            path (str): The absolute path to the file. May be None.
            fp: An open file-like object used for writing.
        """
        self.path = path
        self.validations = []
        self.fp = fp

    @property
    def is_open(self):
        """
        Get whether the writer is open.

        Returns:
            bool: True when open.
        """
        return self.fp is not None

    def open(self):
        """
        Open for writing.
        The directory tree is created as necessary.
        """
        pass

    def append(self, bfr):
        """
        Append (write) the buffer.

        Args:
            bfr (bytes): A buffer to append.

        Returns:
            int: The number of bytes appended.
        """
        for validation in self.validations:
            validation.update(bfr)
        return self.fp.write(bfr)

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
    """

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
        try:
            os.makedirs(os.path.dirname(self.path))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def __str__(self):
        return self.path


class TextWriter(Writer):
    """
    Downloaded text writer.
    Used to store downloaded text in memory.
    """

    def open(self):
        self.fp = BytesIO()

    def __str__(self):
        self.fp.seek(0)
        return self.fp.read().decode('utf8', 'replace')
