
import glob
import gzip
import hashlib
import unittest
import os
import tempfile
import shutil
import sys

from mock import Mock, patch, ANY

from pulp.common.error_codes import PLP1005
from pulp.devel.unit.server.util import assert_validation_exception
from pulp.plugins.util.metadata_writer import MetadataFileContext, JSONArrayFileContext
from pulp.plugins.util.metadata_writer import XmlFileContext
from pulp.plugins.util.metadata_writer import FastForwardXmlFileContext
from pulp.plugins.util.verification import TYPE_SHA1

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))


class MetadataWriterTests(unittest.TestCase):

    def setUp(self):
        self.metadata_file_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.metadata_file_dir)

    def test_metadata_instantiation(self):
        try:
            metadata_file_context = MetadataFileContext('fu.xml')
        except Exception, e:
            self.fail(e.message)

        self.assertEqual(metadata_file_context.checksum_type, None)

    def test_metadata_instantiation_with_checksum_type(self):
        test_checksum_type = 'sha1'

        try:
            metadata_file_context = MetadataFileContext('fu.xml', checksum_type=test_checksum_type)
        except Exception, e:
            self.fail(e.message)

        self.assertEqual(metadata_file_context.checksum_type, 'sha1')
        self.assertEqual(metadata_file_context.checksum_constructor,
                         getattr(hashlib, test_checksum_type))

    def test_open_handle(self):

        path = os.path.join(self.metadata_file_dir, 'open_handle.xml')
        context = MetadataFileContext(path)

        context._open_metadata_file_handle()

        self.assertTrue(os.path.exists(path))

        context._close_metadata_file_handle()

    def test_open_handle_bad_parent_permissions(self):

        parent_path = os.path.join(self.metadata_file_dir, 'parent')
        path = os.path.join(parent_path, 'nope.xml')
        context = MetadataFileContext(path)

        os.makedirs(parent_path, mode=0000)
        self.assertRaises(RuntimeError, context._open_metadata_file_handle)
        os.chmod(parent_path, 0777)

    def test_open_handle_file_exists(self):

        path = os.path.join(self.metadata_file_dir, 'overwriteme.xml')
        context = MetadataFileContext(path)

        with open(path, 'w') as h:
            h.flush()

        context._open_metadata_file_handle()

    def test_open_handle_bad_file_permissions(self):

        path = os.path.join(self.metadata_file_dir, 'nope_again.xml')
        context = MetadataFileContext(path)

        with open(path, 'w') as h:
            h.flush()
        os.chmod(path, 0000)

        self.assertRaises(RuntimeError, context._open_metadata_file_handle)

    def test_open_handle_gzip(self):

        path = os.path.join(self.metadata_file_dir, 'test.xml.gz')
        context = MetadataFileContext(path)

        context._open_metadata_file_handle()

        self.assertTrue(os.path.exists(path))

        context._write_file_header()
        context._close_metadata_file_handle()

        try:
            h = gzip.open(path)

        except Exception, e:
            self.fail(e.message)

        h.close()

    def test_init_invalid_checksum(self):
        path = os.path.join(self.metadata_file_dir, 'foo', 'header.xml')
        assert_validation_exception(MetadataFileContext, [PLP1005], path, checksum_type='invalid')

    def test_initialize(self):

        path = os.path.join(self.metadata_file_dir, 'foo', 'header.xml')
        context = MetadataFileContext(path)

        context._write_file_header = Mock()

        context.initialize()

        context._write_file_header.assert_called_once_with()
        self.assertTrue(os.path.exists(path))

        with open(path) as h:
            content = h.read()
        expected_content = ''
        self.assertEqual(content, expected_content)

    def test_initialize_double_call(self):
        path = os.path.join(self.metadata_file_dir, 'test.xml')
        context = MetadataFileContext(path)
        context.initialize()
        context._write_file_header = Mock()
        context.initialize()
        self.assertEquals(0, context._write_file_header.call_count)
        context.finalize()

    def test_is_closed_gzip_file(self):
        path = os.path.join(os.path.dirname(__file__), '../../../data/foo.tar.gz')

        file_object = gzip.open(path)
        file_object.close()

        self.assertTrue(MetadataFileContext._is_closed(file_object))

    def test_is_open_gzip_file(self):
        path = os.path.join(os.path.dirname(__file__), '../../../data/foo.tar.gz')

        file_object = gzip.open(path)

        self.assertFalse(MetadataFileContext._is_closed(file_object))

        file_object.close()

    def test_is_closed_file(self):
        path = os.path.join(os.path.dirname(__file__), '../../../data/foo.tar.gz')

        # opening as a regular file, not with gzip
        file_object = open(path)
        file_object.close()

        self.assertTrue(MetadataFileContext._is_closed(file_object))

    def test_is_open_file(self):
        path = os.path.join(os.path.dirname(__file__), '../../../data/foo.tar.gz')

        # opening as a regular file, not with gzip
        file_object = open(path)

        self.assertFalse(MetadataFileContext._is_closed(file_object))

        file_object.close()

    def test_is_closed_file_attribute_error(self):
        # passing in a list gives it an object that does not have a closed attribute, thus triggering
        # an Attribute error that cannot be solved with the python 2.6 compatibility code
        self.assertRaises(AttributeError, MetadataFileContext._is_closed, [])

    def test_finalize_closed_gzip_file(self):
        # this test makes sure that we can properly detect the closed state of
        # a gzip file, because on python 2.6 we have to take special measures
        # to do so.
        path = os.path.join(os.path.dirname(__file__), '../../../data/foo.tar.gz')

        context = MetadataFileContext('/a/b/c')
        context.metadata_file_handle = gzip.open(path)
        context.metadata_file_handle.close()

        # just make sure this doesn't complain.
        context.finalize()

    def test_finalize_checksum_type_none(self):

        path = os.path.join(self.metadata_file_dir, 'test.xml')
        context = MetadataFileContext(path)

        context.initialize()
        context._write_file_footer = Mock()
        context.finalize()
        context._write_file_footer.assert_called_once_with()

        self.assertEqual(context.metadata_file_path, path)
        self.assertEqual(context.metadata_file_handle, None)

    def test_finalize_error_on_write_footer(self):
        # Ensure that if the write_file_footer throws an exception we eat it so that
        # if multiple metadata files are being finalized, one error won't cause open
        # file handles on the others

        path = os.path.join(self.metadata_file_dir, 'test.xml')
        context = MetadataFileContext(path)

        context.initialize()
        context._write_file_footer = Mock(side_effect=Exception())
        context.finalize()
        context._write_file_footer.assert_called_once_with()

        self.assertEqual(context.metadata_file_path, path)

    def test_finalize_double_call(self):
        path = os.path.join(self.metadata_file_dir, 'test.xml')
        context = MetadataFileContext(path)

        context.initialize()
        context.finalize()
        context._write_file_footer = Mock(side_effect=Exception())
        context.finalize()
        self.assertEquals(context._write_file_footer.call_count, 0)

    def test_finalize_with_valid_checksum_type(self):

        path = os.path.join(self.metadata_file_dir, 'test.xml')
        checksum_type = 'sha1'
        context = MetadataFileContext(path, checksum_type)

        context._open_metadata_file_handle()
        context._write_file_header()
        context.finalize()

        expected_metadata_file_name = context.checksum + '-' + 'test.xml'
        expected_metadata_file_path = os.path.join(self.metadata_file_dir,
                                                   expected_metadata_file_name)
        self.assertEquals(expected_metadata_file_path, context.metadata_file_path)

    @patch('pulp.plugins.util.metadata_writer._LOG.exception')
    def test_finalize_error_on_footer(self, mock_logger):

        path = os.path.join(self.metadata_file_dir, 'test.xml')
        context = MetadataFileContext(path)
        context._write_file_footer = Mock(side_effect=Exception('foo'))

        context._open_metadata_file_handle()
        context._write_file_header()

        context.finalize()

        self.assertTrue(mock_logger.called)

    @patch('pulp.plugins.util.metadata_writer._LOG.exception')
    def test_finalize_error_on_close(self, mock_logger):

        path = os.path.join(self.metadata_file_dir, 'test.xml')
        context = MetadataFileContext(path)
        context._close_metadata_file_handle = Mock(side_effect=Exception('foo'))

        context._open_metadata_file_handle()
        context._write_file_header()

        context.finalize()

        self.assertTrue(mock_logger.called)

    @patch('pulp.plugins.util.metadata_writer._LOG')
    def test_exit_error(self, mock_log):
        path = os.path.join(self.metadata_file_dir, 'test.xml')
        context = MetadataFileContext(path)
        try:
            raise Exception()
        except Exception:
            ex_type, ex, tb = sys.exc_info()
            context.__exit__(ex_type, ex, tb)
        self.assertEquals(1, mock_log.debug.call_count)

    def test_enter(self):
        path = os.path.join(self.metadata_file_dir, 'test.xml')
        context = MetadataFileContext(path)
        context.initialize = Mock()
        context.__enter__()
        context.initialize.assert_called_once_with()


class TestJSONArrayFileContext(unittest.TestCase):

    def setUp(self):
        self.working_directory = tempfile.mkdtemp()
        self.file_name = os.path.join(self.working_directory, 'foo')
        self.context = JSONArrayFileContext(self.file_name)
        self.context.metadata_file_handle = Mock()

    def tearDown(self):
        shutil.rmtree(self.working_directory)

    def test_write_file_header(self):
        self.context._write_file_header()
        self.context.metadata_file_handle.write.assert_called_once_with('[')

    def test_write_file_footer(self):
        self.context._write_file_footer()
        self.context.metadata_file_handle.write.assert_called_once_with(']')

    def test_add_unit_metadata(self):
        self.context.add_unit_metadata('foo')
        self.assertEquals(self.context.metadata_file_handle.write.call_count, 0)
        self.context.add_unit_metadata('bar')
        self.context.metadata_file_handle.write.assert_called_once_with(',')


class XmlFileContextTests(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp()
        self.tag = 'metadata'
        self.attributes = {'packages': '30'}
        self.context = XmlFileContext(os.path.join(self.working_dir, 'test.xml'),
                                      self.tag, self.attributes)

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    @patch('pulp.plugins.util.metadata_writer.XMLGenerator')
    def test_init_with_arguments(self, mock_generator):
        self.assertEquals(self.context.root_attributes, self.attributes)
        self.assertEquals(self.context.root_tag, 'metadata')

    @patch('pulp.plugins.util.metadata_writer.XMLGenerator')
    def test_init_with_no_properties(self, mock_generator):
        self.context = XmlFileContext(os.path.join(self.working_dir, 'test.xml'),
                                      self.tag)
        self.assertEquals(self.context.root_attributes, {})
        self.assertEquals(self.context.root_tag, 'metadata')

    @patch('pulp.plugins.util.metadata_writer.XMLGenerator')
    def test_open_metadata_file_handle(self, mock_generator):
        self.context._open_metadata_file_handle()
        mock_generator.assert_called_once_with(self.context.metadata_file_handle, 'UTF-8')

    @patch('pulp.plugins.util.metadata_writer.XMLGenerator')
    def test_write_file_header(self, mock_generator):
        self.context._open_metadata_file_handle()
        self.context._write_file_header()
        mock_generator.return_value.startDocument.assert_called_once()
        mock_generator.return_value.startElement.assert_called_once_with(self.tag, self.attributes)

    @patch('pulp.plugins.util.metadata_writer.XMLGenerator')
    def test_write_file_footer(self, mock_generator):
        self.context._open_metadata_file_handle()
        self.context._write_file_footer()
        mock_generator.return_value.endElement.assert_called_once_with(self.tag)
        mock_generator.return_value.endDocument.assert_called_once()


class FastForwardXmlFileContextTests(unittest.TestCase):

    def setUp(self):
        self.working_dir = tempfile.mkdtemp()
        expression = os.path.join(DATA_DIR, 'metadata', '*')
        for file_name in glob.glob(expression):
            shutil.copy(file_name, self.working_dir)
        self.tag = 'metadata'
        self.attributes = {'packages': '30'}

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    @patch('pulp.plugins.util.metadata_writer.XMLGenerator')
    def test_open_metadata_file_handle_non_existent_file(self, mock_generator):
        os.remove(os.path.join(self.working_dir, 'test.xml'))
        context = FastForwardXmlFileContext(os.path.join(self.working_dir, 'test.xml'),
                                            self.tag, 'packages', self.attributes)
        context._open_metadata_file_handle()
        self.assertFalse(context.fast_forward)

    @patch('pulp.plugins.util.metadata_writer.XMLGenerator')
    def test_open_metadata_file_handle_existing_file(self, mock_generator):
        context = FastForwardXmlFileContext(os.path.join(self.working_dir, 'test.xml'),
                                            self.tag, 'package', self.attributes)
        context._open_metadata_file_handle()
        self.assertTrue(context.fast_forward)
        # check that the file has been renamed
        self.assertEquals(context.existing_file, os.path.join(self.working_dir, 'original.test.xml'))

    @patch('pulp.plugins.util.metadata_writer.XMLGenerator')
    def test_open_metadata_file_handle_existing_gzip_file(self, mock_generator):
        context = FastForwardXmlFileContext(os.path.join(self.working_dir, 'test.xml.gz'),
                                            self.tag, 'package', self.attributes)
        context._open_metadata_file_handle()
        self.assertTrue(context.fast_forward)
        self.assertEquals(context.existing_file,
                          os.path.join(self.working_dir, 'original.test.xml'))

    @patch('pulp.plugins.util.metadata_writer.XMLGenerator')
    def test_open_metadata_file_handle_existing_checksum_file(self, mock_generator):
        context = FastForwardXmlFileContext(os.path.join(self.working_dir, 'test.xml'),
                                            self.tag, 'package', self.attributes,
                                            checksum_type=TYPE_SHA1)
        context._open_metadata_file_handle()
        self.assertTrue(context.fast_forward)
        self.assertEquals(context.existing_file, os.path.join(self.working_dir, 'aa-test.xml'))

    @patch('pulp.plugins.util.metadata_writer.BUFFER_SIZE', new=8)
    def test_write_file_header_fast_forward_small_buffer(self):
        self._test_fast_forward('test.xml')

    @patch('pulp.plugins.util.metadata_writer.BUFFER_SIZE', new=2500)
    def test_write_file_header_fast_forward_large_buffer(self):
        self._test_fast_forward('test.xml')

    def _test_fast_forward(self, test_file, test_content=None):
        """
        :param test_file: The name of the file in the data/metadata/* directory to use for testing
        :type test_file: str
        :param test_content: The string to compare against.  If not specified the content of
                             test_file is used
        :type test_content: str
        """
        test_file = os.path.join(self.working_dir, test_file)
        if test_content is None:
            test_content = ''
            with open(test_file) as test_file_handle:
                content = test_file_handle.read()
                while content:
                    test_content += content
                    content = test_file_handle.read()
            test_content = test_content[:test_content.rfind('</metadata')]
        context = FastForwardXmlFileContext(test_file,
                                            self.tag, 'package', self.attributes)

        context._open_metadata_file_handle()
        # Ensure the context doesn't find the opening tag during the initial search
        context._write_file_header()
        context.metadata_file_handle.close()
        created_content = ''
        with open(test_file) as test_file_handle:
            content = test_file_handle.read()
            while content:
                created_content += content
                content = test_file_handle.read()
        self.assertEquals(test_content, created_content)

    def test_write_file_header_fast_forward_empty_file(self):
        test_content = '<?xml version="1.0" encoding="UTF-8"?>\n<metadata packages="30">'
        self._test_fast_forward('test_empty.xml', test_content)

    def test_write_file_header_fast_forward_missing_search_tag(self):
        self._test_fast_forward('test_missing_search_tag.xml')

    def test_write_file_header_fast_forward_missing_end_tag(self):
        self.assertRaises(Exception, self._test_fast_forward, 'test_missing_end_tag.xml')

    @patch('pulp.plugins.util.metadata_writer.BUFFER_SIZE', new=8)
    def test_write_file_header_fast_forward_small_buffer_gzip(self):
        test_file = os.path.join(self.working_dir, 'test.xml.gz')
        test_content = ''

        test_file_handle = gzip.open(test_file)
        content = test_file_handle.read()
        while content:
            test_content += content
            content = test_file_handle.read()
        test_file_handle.close()
        test_content = test_content[:test_content.rfind('</metadata')]
        context = FastForwardXmlFileContext(test_file,
                                            self.tag, 'package', self.attributes)

        context._open_metadata_file_handle()
        # Ensure the context doesn't find the opening tag during the initial search
        context._write_file_header()
        context.metadata_file_handle.close()
        created_content = ''
        test_file_handle = gzip.open(test_file)
        content = test_file_handle.read()
        while content:
            created_content += content
            content = test_file_handle.read()
        test_file_handle.close()
        self.assertEquals(test_content, created_content)


    @patch('pulp.plugins.util.metadata_writer.XMLGenerator')
    def test_write_file_header_no_fast_forward(self, mock_generator):
        context = FastForwardXmlFileContext(os.path.join(self.working_dir, 'aa.xml'),
                                            self.tag, self.attributes)

        context._open_metadata_file_handle()
        context._write_file_header()
        mock_generator.return_value.startDocument.assert_called_once_with()

    def test_close_metadata_file_handle_cleans_up_file(self):
        context = FastForwardXmlFileContext(os.path.join(self.working_dir, 'test.xml'),
                                            self.tag, self.attributes,
                                            checksum_type=TYPE_SHA1)
        context._open_metadata_file_handle()
        context._close_metadata_file_handle()
        self.assertFalse(os.path.exists(os.path.join(self.working_dir, 'aa-test.xml')))

    def test_close_metadata_file_handle_no_fast_forward(self):
        context = FastForwardXmlFileContext(os.path.join(self.working_dir, 'test.xml'),
                                            self.tag, self.attributes, checksum_type=TYPE_SHA1)
        context._open_metadata_file_handle()
        context._close_metadata_file_handle()
        self.assertTrue(context._is_closed(context.metadata_file_handle))
