# -*- coding: utf-8 -*-

from cStringIO import StringIO

from pulp.common.compat import unittest
from pulp.plugins.util.saxwriter import XMLWriter


class TestXMLWriter(unittest.TestCase):
    """
    Test the correct generation of XML using XMLWriter class.
    """
    def _calls_to_test_xml_generator(self):
        """
        Sequence of calls which test all the methods of XMLWriter class.
        """
        self.xml_generator.startDocument()
        self.xml_generator.writeDoctype('<!DOCTYPE string here>')
        self.xml_generator.startElement('outer_tag1')
        self.xml_generator.completeElement('inner_tag1', {}, 'content in utf-8')
        self.xml_generator.completeElement('inner_tag2', {'attr1': 'value1'}, u'content in unicode')
        self.xml_generator.completeElement('inner_tag3', {'attr1': None, 'attr2': 'value2'}, None)
        self.xml_generator.endElement('outer_tag1')
        self.xml_generator.startElement('outer_tag2')
        self.xml_generator.endElement('outer_tag2')
        self.xml_generator.endDocument()

    def test_short_empty_elements_true(self):
        """
        Test that XML is generated correctly and a short form of empty element is used.
        """
        fake_file = StringIO()
        self.xml_generator = XMLWriter(fake_file, short_empty_elements=True)
        self._calls_to_test_xml_generator()
        generated_xml = fake_file.getvalue()
        fake_file.close()
        expected_xml = '<?xml version="1.0" encoding="utf-8"?>\n' \
                       '<!DOCTYPE string here>\n' \
                       '<outer_tag1>\n' \
                       '  <inner_tag1>content in utf-8</inner_tag1>\n' \
                       '  <inner_tag2 attr1="value1">content in unicode</inner_tag2>\n' \
                       '  <inner_tag3 attr2="value2" />\n' \
                       '</outer_tag1>\n' \
                       '<outer_tag2 />\n'
        self.assertEqual(generated_xml, expected_xml)

    def test_short_empty_elements_false(self):
        """
        Test that XML is generated correctly and a short form of empty element is not used.
        """
        fake_file = StringIO()
        self.xml_generator = XMLWriter(fake_file)
        self._calls_to_test_xml_generator()
        generated_xml = fake_file.getvalue()
        fake_file.close()
        expected_xml = '<?xml version="1.0" encoding="utf-8"?>\n' \
                       '<!DOCTYPE string here>\n' \
                       '<outer_tag1>\n' \
                       '  <inner_tag1>content in utf-8</inner_tag1>\n' \
                       '  <inner_tag2 attr1="value1">content in unicode</inner_tag2>\n' \
                       '  <inner_tag3 attr2="value2"></inner_tag3>\n' \
                       '</outer_tag1>\n' \
                       '<outer_tag2></outer_tag2>\n'
        self.assertEqual(generated_xml, expected_xml)

    def test_utf8_writes(self):
        """
        Test that utf-8 non-ascii characters are handled without complaint.
        """
        xml_generator = XMLWriter(StringIO())

        tag = u'𝅘𝅥𝅮'
        xml_generator.startDocument()
        xml_generator.writeDoctype('<!DOCTYPE string here>')
        xml_generator.startElement(tag, {u'𝆑': u'𝆒'})
        xml_generator.completeElement(u'inner_tag2 Ώ', {u'attr1 ỳ': u'value1 ỳ'}, u'ỳ')
        xml_generator.endElement(tag)
        xml_generator.endDocument()
