import xmlrpclib
import gzip
import StringIO
import xml.dom.minidom

class TransportWithHeaders(xmlrpclib.Transport):
    def __init__(self):
        if hasattr(xmlrpclib.Transport, '__init__'):
            xmlrpclib.Transport.__init__(self)
        self.props = {}

    def addProperty(self, key, value):
        self.props[key] = value

    def getProperty(self, key):
        return self.props[key]

    def send_host(self, connection, host):
        for key in self.props:
            connection.putheader(key, self.props[key])

#Issues
#1) Need add custom header
#2) Data comes back gzipped, need to read it (seems like latest python in svn has support, yet python 2.6 doesn't)
#3) xml message doesn't conform to xmlrpc standard
#
class GzipDecodedString(gzip.GzipFile):
    """a file-like object to decode a response encoded with the gzip
    method, as described in RFC 1952.
    """
    def __init__(self, data):
        if not gzip:
            raise NotImplementedError
        self.stringio = StringIO.StringIO(data)
        gzip.GzipFile.__init__(self, mode="rb", fileobj=self.stringio)

    def close(self):
        gzip.GzipFile.close(self)
        self.stringio.close()

class RHNTransport(TransportWithHeaders):
    ##
    # Parse response (alternate interface).  This is similar to the
    # parse_response method, but also provides direct access to the
    # underlying socket object (where available).
    #
    # @param file Stream.
    # @param sock Socket handle (or None, if the socket object
    #    could not be accessed).
    # @return Response tuple and target method.
    def _parse_response(self, file, sock):
        response = ""
        while 1:
            if sock:
                snippet = sock.recv(1024)
            else:
                snippet = file.read(1024)
            if not snippet:
                break
            response += snippet
        #
        # TODO:
        # Would prefer to grab header and read if data is gzip or not before doing below, but not
        # sure how to access header here.
        #
        try: 
            gzipDecodeStr = GzipDecodedString(response)
            unzippedResponse = gzipDecodeStr.read()
        except IOError, e:
            #Error messages from RHN are not gzipped, bust most (maybe all) data calls will be
            unzippedResponse = response

        if self.verbose:
            print "body:", repr(unzippedResponse)
        
        if file:
            file.close()
        if sock:
            sock.close()

        p, u = self.getparser()
        p.feed(unzippedResponse)
        # First try to parse as a standard XMLRPC response XML.  If that 
        # fails just return the DOM object
        try:
            retval = u.close()
            return retval
        except xmlrpclib.ResponseError, re:
            dom = xml.dom.minidom.parseString(unzippedResponse)
            # HACK, __request expects what we return to support "len()", 
            # so throwing this in a list for now
            return [dom]
        
