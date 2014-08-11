from gettext import gettext as _
import glob
import gzip
import logging
import os
import shutil
import traceback


from xml.sax.saxutils import XMLGenerator

from pulp.common import error_codes
from pulp.server.exceptions import PulpCodedValidationException, PulpCodedException
from verification import CHECKSUM_FUNCTIONS

_LOG = logging.getLogger(__name__)
BUFFER_SIZE = 1024


class MetadataFileContext(object):
    """
    Context manager class for metadata file generation.
    """

    def __init__(self, metadata_file_path, checksum_type=None):
        """
        :param metadata_file_path: full path to metadata file to be generated
        :type  metadata_file_path: str
        :param checksum_type: checksum type to be used to generate and prepend checksum
                              to the file names of files. If checksum_type is None,
                              no checksum is added to the filename
        :type checksum_type: str or None
        """

        self.metadata_file_path = metadata_file_path
        self.metadata_file_handle = None
        self.checksum_type = checksum_type
        self.checksum = None
        if self.checksum_type is not None:
            checksum_function = CHECKSUM_FUNCTIONS.get(checksum_type)
            if not checksum_function:
                raise PulpCodedValidationException(
                    [PulpCodedException(error_codes.PLP1005, checksum_type=checksum_type)])
            self.checksum_constructor = checksum_function

    def __enter__(self):

        self.initialize()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        if None not in (exc_type, exc_val, exc_tb):

            err_msg = '\n'.join(traceback.format_exception(exc_type, exc_val, exc_tb))
            log_msg = _('Exception occurred while writing [%(m)s]\n%(e)s')
            # any errors here should have already been caught and logged
            _LOG.debug(log_msg % {'m': self.metadata_file_path, 'e': err_msg})

        self.finalize()

        return True

    def initialize(self):
        """
        Create the new metadata file and write the header.
        """
        if self.metadata_file_handle is not None:
            # initialize has already, at least partially, been run
            return

        self._open_metadata_file_handle()
        self._write_file_header()

    def finalize(self):
        """
        Write the footer into the metadata file and close it.
        """
        if self._is_closed(self.metadata_file_handle):
            # finalize has already been run or initialize has not been run
            return

        try:
            self._write_file_footer()

        except Exception, e:
            _LOG.exception(e)

        try:
            self._close_metadata_file_handle()

        except Exception, e:
            _LOG.exception(e)

        # Add calculated checksum to the filename
        file_name = os.path.basename(self.metadata_file_path)
        if self.checksum_type is not None:
            with open(self.metadata_file_path, 'rb') as file_handle:
                content = file_handle.read()
                checksum = self.checksum_constructor(content).hexdigest()

            self.checksum = checksum
            file_name_with_checksum = checksum + '-' + file_name
            new_file_path = os.path.join(os.path.dirname(self.metadata_file_path),
                                         file_name_with_checksum)
            os.rename(self.metadata_file_path, new_file_path)
            self.metadata_file_path = new_file_path

        # Set the metadata_file_handle to None so we don't double call finalize
        self.metadata_file_handle = None

    def _open_metadata_file_handle(self):
        """
        Open the metadata file handle, creating any missing parent directories.

        If the file already exists, this will overwrite it.
        """
        assert self.metadata_file_handle is None
        _LOG.debug('Opening metadata file: %s' % self.metadata_file_path)

        if not os.path.exists(self.metadata_file_path):

            parent_dir = os.path.dirname(self.metadata_file_path)

            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, mode=0770)

            elif not os.access(parent_dir, os.R_OK | os.W_OK | os.X_OK):
                msg = _('Insufficient permissions to write metadata file in directory [%(d)s]')
                raise RuntimeError(msg % {'d': parent_dir})

        else:

            msg = _('Overwriting existing metadata file [%(p)s]')
            _LOG.warn(msg % {'p': self.metadata_file_path})

            if not os.access(self.metadata_file_path, os.R_OK | os.W_OK):
                msg = _('Insufficient permissions to overwrite [%(p)s]')
                raise RuntimeError(msg % {'p': self.metadata_file_path})

        msg = _('Opening metadata file handle for [%(p)s]')
        _LOG.debug(msg % {'p': self.metadata_file_path})

        if self.metadata_file_path.endswith('.gz'):
            self.metadata_file_handle = gzip.open(self.metadata_file_path, 'w')

        else:
            self.metadata_file_handle = open(self.metadata_file_path, 'w')

    def _write_file_header(self):
        """
        Write any headers for the metadata file
        """
        pass

    def _write_file_footer(self):
        """
        Write any file footers for the metadata file.
        """
        pass

    def _close_metadata_file_handle(self):
        """
        Flush any cached writes to the metadata file handle and close it.
        """
        _LOG.debug('Closing metadata file: %s' % self.metadata_file_path)
        if not self._is_closed(self.metadata_file_handle):
            self.metadata_file_handle.flush()
            self.metadata_file_handle.close()

    @staticmethod
    def _is_closed(file_object):
        """
        Determine if the file object has been closed. If it is None, it is assumed to be closed.

        :param file_object: a file object
        :type  file_object: file

        :return:    True if the file object is closed or is None, otherwise False
        :rtype:     bool
        """
        if file_object is None:
            # finalize has already been run or initialize has not been run
            return True

        try:
            return file_object.closed
        except AttributeError:
            # python 2.6 doesn't have a "closed" attribute on a GzipFile,
            # so we must look deeper.
            if isinstance(file_object, gzip.GzipFile):
                return file_object.myfileobj is None or file_object.myfileobj.closed
            else:
                raise


class JSONArrayFileContext(MetadataFileContext):
    """
    Context manager for writing out units as a json array.
    """

    def __init__(self, *args, **kwargs):
        """

        :param args: any positional arguments to be passed to the superclass
        :type  args: list
        :param kwargs: any keyword arguments to be passed to the superclass
        :type  kwargs: dict
        """

        super(JSONArrayFileContext, self).__init__(*args, **kwargs)
        self.units_added = False

    def _write_file_header(self):
        """
        Write out the beginning of the json file
        """
        self.metadata_file_handle.write('[')

    def _write_file_footer(self):
        """
        Write out the end of the json file
        """
        self.metadata_file_handle.write(']')

    def add_unit_metadata(self, unit):
        """
        Add the specific metadata for this unit
        """
        if self.units_added:
            self.metadata_file_handle.write(',')
        else:
            self.units_added = True


class XmlFileContext(MetadataFileContext):
    """
    Context manager for writing out units as xml
    """

    def __init__(self, metadata_file_path, root_tag, root_attributes=None, *args, **kwargs):
        """
        :param metadata_file_path: The file path for the file to write
        :type metadata_file_path: str
        :param root_tag: The root tag for the xml tree
        :type root_tag: str
        :param root_attributes: Any attributes to populate on the root xml tag
        :type root_attributes: dict of str
        :param args: any positional arguments to be passed to the superclass
        :type  args: list
        :param kwargs: any keyword arguments to be passed to the superclass
        :type  kwargs: dict
        """

        super(XmlFileContext, self).__init__(metadata_file_path, *args, **kwargs)
        self.root_tag = root_tag
        if not root_attributes:
            root_attributes = {}
        self.root_attributes = root_attributes

    def _open_metadata_file_handle(self):
        """
        Open the metadata file handle, creating any missing parent directories.

        If the file already exists, this will overwrite it.
        """
        super(XmlFileContext, self)._open_metadata_file_handle()
        self.xml_generator = XMLGenerator(self.metadata_file_handle, 'UTF-8')

    def _write_file_header(self):
        """
        Write out the beginning of the json file
        """
        self.xml_generator.startDocument()
        self.xml_generator.startElement(self.root_tag, self.root_attributes)

    def _write_file_footer(self):
        """
        Write out the end of the json file
        """
        self.xml_generator.endElement(self.root_tag)
        self.xml_generator.endDocument()


class FastForwardXmlFileContext(XmlFileContext):
    """
    Context manager for reopening an existing XML file context to insert more data.
    """

    def __init__(self, metadata_file_path, root_tag, search_tag, root_attributes=None,
                 *args, **kwargs):
        """
        :param metadata_file_path: The file path for the file to write
        :type metadata_file_path: str
        :param root_tag: The root tag for the xml tree
        :type root_tag: str
        :param search_tag: The tag that denotes the beginning of content to copy
        :param root_attributes: Any attributes to populate on the root xml tag
        :type root_attributes: dict of str
        :param args: any positional arguments to be passed to the superclass
        :type  args: list
        :param kwargs: any keyword arguments to be passed to the superclass
        :type  kwargs: dict
        """
        super(FastForwardXmlFileContext, self).__init__(metadata_file_path, root_tag,
                                                        root_attributes, *args, **kwargs)
        self.fast_forward = False
        self.search_tag = search_tag
        self.existing_file = None
        self.xml_generator = None

    def _open_metadata_file_handle(self):
        """
        Open the metadata file handle, creating any missing parent directories.

        If the file already exists, this will copy it to a new name and open it as an input
        for filtering/modification.
        """
        # Figure out if we are fast forwarding a file
        # find the primary file
        working_dir, file_name = os.path.split(self.metadata_file_path)
        if self.checksum_type:
            # Look for a file matching the checksum-filename pattern
            expression = '[0-9a-zA-Z]*-%s' % file_name
            expression = os.path.join(working_dir, expression)
            file_list = glob.glob(expression)
            if file_list:
                self.existing_file = file_list[0]
                self.fast_forward = True
        elif not self.checksum_type and os.path.exists(self.metadata_file_path):
            self.existing_file = file_name
            self.fast_forward = True

        if self.fast_forward:
            # move the file so that we can still process it if the name is the same
            if self.existing_file == file_name:
                new_file_name = 'original.%s' % self.existing_file
                shutil.move(os.path.join(working_dir, self.existing_file),
                            os.path.join(working_dir, new_file_name))
                self.existing_file = new_file_name

            self.existing_file = os.path.join(working_dir, self.existing_file)

            # Open the file, unzip if necessary so that seek operations can be performed
            self.original_file_handle = None
            if self.existing_file.endswith('.gz'):
                non_compressed_file = self.existing_file[:self.existing_file.rfind('.gz')]
                with open(os.path.join(working_dir, non_compressed_file), 'wb') as plain_handle:
                    gzip_handle = gzip.open(os.path.join(working_dir, self.existing_file), 'rb')
                    try:
                        content = gzip_handle.read(BUFFER_SIZE)
                        while content:
                            plain_handle.write(content)
                            content = gzip_handle.read(BUFFER_SIZE)
                    finally:
                        if gzip_handle:
                            gzip_handle.close()
                self.existing_file = non_compressed_file

            self.original_file_handle = open(os.path.join(working_dir, self.existing_file), 'r')

        super(FastForwardXmlFileContext, self)._open_metadata_file_handle()

    def _write_file_header(self):
        """
        Write out the beginning of the file only if we are not in fast forward mode
        """
        super(FastForwardXmlFileContext, self)._write_file_header()
        if self.fast_forward:
            start_tag = '<%s' % self.search_tag
            end_tag = '</%s' % self.root_tag

            # Find the start offset
            content = ''
            index = -1
            while index < 0:
                content_buffer = self.original_file_handle.read(BUFFER_SIZE)
                if not content_buffer:
                    # The search tag was never found, This is an empty file where no FF is necessary
                    msg = _('When attempting to fast forward the file %(file)s, the search tag '
                            '%(tag)s was not found so the assumption is that no fast forward is to '
                            'take place.')
                    _LOG.debug(msg, {'file': self.metadata_file_path, 'tag': start_tag})
                    return
                content += content_buffer
                index = content.find(start_tag)
            start_offset = index

            # Find the end offset
            content = ''
            index = -1
            self.original_file_handle.seek(0, os.SEEK_END)
            while index < 0:
                amount_to_read = min(BUFFER_SIZE, self.original_file_handle.tell())
                self.original_file_handle.seek(-amount_to_read, os.SEEK_CUR)
                content_buffer = self.original_file_handle.read(amount_to_read)
                if not content_buffer:
                    raise Exception(_('Error: %(tag)s not found in the xml file.')
                                    % {'tag': end_tag})
                bytes_read = len(content_buffer)
                self.original_file_handle.seek(-bytes_read, os.SEEK_CUR)
                content = content_buffer + content
                index = content.rfind(end_tag)
            end_offset = self.original_file_handle.tell() + index

            # stream out the content
            self.original_file_handle.seek(start_offset)
            bytes_to_read = end_offset - start_offset
            content_buffer = self.original_file_handle.read(BUFFER_SIZE)
            while bytes_to_read > 0:
                buffer_size = len(content_buffer)
                if buffer_size > bytes_to_read:
                    content_buffer = content_buffer[:bytes_to_read]
                self.metadata_file_handle.write(content_buffer)
                bytes_to_read -= buffer_size
                content_buffer = self.original_file_handle.read(BUFFER_SIZE)

    def _close_metadata_file_handle(self):
        """
        Close any open file handles and remove the original file if a new one
        was generated
        """
        super(FastForwardXmlFileContext, self)._close_metadata_file_handle()
        # Close & remove the existing file that was copied
        if self.fast_forward:
            if not self._is_closed(self.original_file_handle):
                self.original_file_handle.close()
            # We will always have renamed the original file so remove it
            os.unlink(self.existing_file)
