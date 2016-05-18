from xml.sax.handler import ContentHandler
from xml.sax.saxutils import escape, quoteattr


class XMLWriter(ContentHandler):
    """
    XML writer similar to xml.sax.saxutils.XMLGenerator.
    The result is indented XML, which is written sequentially to the stream.
    xml.sax.saxutils.XMLGenerator is not used as is because of the lack of the
    following functionality:
     - short_empty_elements flag which is backported from Python 3.5.1 xml.sax.saxutils.XMLGenerator
     - ability to generate an indented XML

    :ivar _pending_start_element: indicates that element was started but it is not clear yet if it
                                  should be closed right away or there will be some content. Needed
                                  for generation of the empty elements in a short form. Backported
                                  from Python 3.5.1 xml.sax.saxutils.XMLGenerator.
    :type _pending_start_element: bool
    :ivar _indent_lvl: current level of indentation. Needed to generate proper indentation.
    :type _indent_lvl: int
    :ivar _indent_sep: indentation separator. Needed to generate proper indentation.
    :type _indent_sep: str
    :ivar _start_element: indicates that element was started and not ended yet. Needed to generate
                          proper indentation.
    :type _start_element: bool
    """

    def __init__(self, stream, encoding='utf-8', short_empty_elements=False):
        """
        :param stream: a stream to write XML to
        :type  stream: file-like object
        :param encoding: encoding of the generated XML
        :type  encoding: str
        :param short_empty_elements: indicates that the empty elements should be generated in
                                     a short form. Backported from Python 3.5.1
                                     xml.sax.saxutils.XMLGenerator.
        :type  short_empty_elements: bool
        """
        ContentHandler.__init__(self)
        self._write = stream.write
        self._flush = stream.flush
        self._encoding = encoding
        self._short_empty_elements = short_empty_elements
        self._pending_start_element = False
        self._indent_lvl = 0
        self._indent_sep = '  '
        self._start_element = False

    def _finish_pending_start_element(self):
        """
        Finish start of the element. Backported from Python 3.5.1 xml.sax.saxutils.XMLGenerator.
        """
        if self._pending_start_element:
            self._write('>')
            self._pending_start_element = False

    def writeDoctype(self, doctype_str):
        """
        Write a doctype string to the stream.

        :param doctype_str: doctype string to write to the stream
        :type  doctype_str: str
        """
        self._write(doctype_str + '\n')

    def completeElement(self, name, attrs, text):
        """
        Write a complete element to the stream.

        :param name: name of the tag
        :type  name: str

        :param attrs: element attributes
        :type  attrs: dict

        :param text: content of the element
        :type  text: str
        """
        self.startElement(name, attrs)
        self.characters(text)
        self.endElement(name)

    # ContentHandler methods

    def startDocument(self):
        """
        Write the prolog to define XML version and encoding.
        """
        self._write('<?xml version="1.0" encoding="%s"?>\n' % self._encoding)

    def endDocument(self):
        """
        Flush the buffer after generating the XML document.
        """
        self._flush()

    def startElement(self, name, attrs={}):
        """
        Start the element.

        :param name: name of the element
        :type  name: str
        :param attrs: element attributes
        :type  attrs: dict
        """
        self._finish_pending_start_element()
        if self._start_element:
            self._write('\n')
            self._indent_lvl += 1
        self._write(self._indent_sep * self._indent_lvl)
        self._write('<' + name)
        for name, value in attrs.items():
            if value is not None:
                self._write(' %s=%s' % (name, quoteattr(value)))
        if self._short_empty_elements:
            self._pending_start_element = True
        else:
            self._write(">")
        self._start_element = True

    def endElement(self, name):
        """
        End the element.

        :param name: name of the element
        :type  name: str
        """
        if self._pending_start_element:
            self._write(' />\n')
            self._pending_start_element = False
        else:
            if not self._start_element:
                self._indent_lvl -= 1
                self._write(self._indent_sep * self._indent_lvl)
            self._write('</%s>\n' % name)
        self._start_element = False

    def characters(self, content):
        """
        Write the content of the element.

        :param content: content of the element
        :type  content: str
        """
        if content:
            self._finish_pending_start_element()
            if isinstance(content, unicode):
                self._write(escape(content).encode(self._encoding))
            else:
                self._write(escape(content))
