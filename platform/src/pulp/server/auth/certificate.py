#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""
Contains classes for working with x.509 certificates.
The backing implementation is M2Crypto.X509 which has insufficient
support for custom v3 extensions.  It is not intended to be a
replacement of full wrapper but instead and extension.
"""

import logging
import os
import re
from datetime import datetime as dt

from M2Crypto import X509

from pulp.common import dateutils
from pulp.common.util import encode_unicode

log = logging.getLogger(__name__)

class Certificate(object):
    """
    Represents and x.509 certificate.
    @ivar x509: The M2Crypto.X509 backing object.
    @type x509: L{X509}
    @ivar __ext: A dictionary of extensions L{OID}:value
    @type __ext: L{Extensions}
    """

    def __init__(self, content=None):
        """
        @param content: The (optional) PEM encoded content.
        @type content: str
        """
        self.update(content)

    def update(self, content):
        if content:
            x509 = X509.load_cert_string(content)
        else:
            x509 = X509.X509()
        self.__ext = Extensions(x509)
        self.x509 = x509

    def serialNumber(self):
        """
        Get the serial number
        @return: The x.509 serial number
        @rtype: str
        """
        return self.x509.get_serial_number()

    def subject(self):
        """
        Get the certificate subject.
        note: Missing NID mapping for UID added to patch openssl.
        @return: A dictionary of subject fields.
        @rtype: dict
        """
        d = {}
        subject = self.x509.get_subject()
        subject.nid['UID'] = 458
        for key, nid in subject.nid.items():
            entry = subject.get_entries_by_nid(nid)
            if len(entry):
                asn1 = entry[0].get_data()
                try:
                    d[key] = str(asn1)
                except UnicodeEncodeError:
                    d[key] = encode_unicode(asn1)
                continue
        return d

    def validRange(self):
        """
        Get the I{valid} date range.
        @return: The valid date range.
        @rtype: L{DateRange}
        """
        return DateRange(self.x509)

    def valid(self):
        """
        Get whether the certificate is valid based on date.
        @return: True if valid.
        @rtype: boolean
        """
        return self.validRange().hasNow()

    def bogus(self):
        """
        Get whether the certificate contains bogus
        data or is otherwise unsuitable.  The certificate
        may be valid but still be considered bogus.
        @return: List of reasons if bogus
        @rtype: list
        """
        return []

    def extensions(self):
        """
        Get custom extensions.
        @return: An extensions object.
        @rtype: L{Extensions}
        """
        return self.__ext

    def read(self, path):
        """
        Read a certificate file.
        @param path: The path to a .pem file.
        @type path: str
        @return: A certificate
        @rtype: L{Certificate}
        """
        f = open(path)
        content = f.read()
        try:
            self.update(content)
        finally:
            f.close()
        self.path = path

    def write(self, path):
        """
        Write the certificate.
        @param path: The path to the .pem file.
        @type path: str
        @return: self
        """
        f = open(path, 'w')
        f.write(self.toPEM())
        self.path = path
        f.close()
        return self

    def delete(self):
        """
        Delete the file associated with this certificate.
        """
        if hasattr(self, 'path'):
            os.unlink(self.path)
        else:
            raise Exception, 'no path, not deleted'

    def toPEM(self):
        """
        Get PEM representation of the certificate.
        @return: A PEM string
        @rtype: str
        """
        return self.x509.as_pem()

    def __str__(self):
        return self.x509.as_text()

    def __repr__(self):
        sn = self.serialNumber()
        path = None
        if hasattr(self, 'path'):
            path = self.path
        return '[sn: %d, path: "%s"]' % (sn, path)

    def __cmp__(self, other):
        range = self.validRange()
        exp1 = range.end()
        range = other.validRange()
        exp2 = range.end()
        if exp1 < exp2:
            return -1
        if exp1 > exp2:
            return 1
        return 0


class Key(object):
    """
    The (private|public) key.
    @ivar content: The PEM encoded key.
    @type content: str
    """

    @classmethod
    def read(cls, path):
        """
        Read the key.
        @param path: The path to the .pem file.
        @type path: str
        """
        f = open(path)
        content = f.read()
        f.close()
        key = Key(content)
        key.path = path
        return key

    def __init__(self, content):
        """
        @param content: The PEM encoded key.
        @type content: str
        """
        self.content = content

    def write(self, path):
        """
        Write the key.
        @param path: The path to the .pem file.
        @type path: str
        @return: self
        """
        f = open(path, 'w')
        f.write(self.content)
        self.path = path
        f.close()
        return self

    def delete(self):
        """
        Delete the file associated with this key.
        """
        if hasattr(self, 'path'):
            os.unlink(self.path)
        else:
            raise Exception, 'no path, not deleted'

    def __str__(self):
        return self.content


class DateRange:
    """
    Date range object converts between ASN1 and python
    datetime objects.
    @ivar x509: A certificate.
    @type x509: X509
    """

    ASN1_FORMAT = '%b %d %H:%M:%S %Y %Z'

    def __init__(self, x509):
        """
        @param x509: A certificate.
        @type x509: X509
        """
        self.range = \
            (str(x509.get_not_before()),
             str(x509.get_not_after()))

    def begin(self):
        """
        Get range beginning.
        @return: The beginning date in UTC.
        @rtype: L{datetime.datetime}
        """
        return self.__parse(self.range[0])

    def end(self):
        """
        Get range end.
        @return: The end date in UTC.
        @rtype: L{datetime.datetime}
        """
        return self.__parse(self.range[1])

    def hasNow(self):
        """
        Get whether the certificate is valid based on date.
        @return: True if valid.
        @rtype: boolean
        """
        gmt = dt.utcnow()
        gmt = gmt.replace(tzinfo=GMT())
        return ( gmt >= self.begin() and gmt <= self.end() )

    def __parse(self, asn1):
        try:
            d = dt.strptime(asn1, self.ASN1_FORMAT)
        except:
            d = dt(year=2000, month=1, day=1)
        return d.replace(tzinfo=GMT())

    def __str__(self):
        return '\n\t%s\n\t%s' % self.range


# GMT used to be a class, now it's a function returning an instance
# left in for backwards compatability and general unwilliness to refactor
# working code
GMT = dateutils.utc_tz


class Extensions(dict):
    """
    Represents x.509 (v3) I{custom} extensions.
    """

    pattern = re.compile('([0-9]+\.)+[0-9]+:')

    def __init__(self, x509):
        """
        @param x509: A certificate object.
        @type x509: L{X509}
        """
        if isinstance(x509, dict):
            self.update(x509)
        else:
            self.__parse(x509)

    def ltrim(self, n):
        """
        Left trim I{n} parts.
        @param n: The number of parts to trim.
        @type n: int
        @return: The trimmed OID
        @rtype: L{Extensions}
        """
        d = {}
        for oid,v in self.items():
            d[oid.ltrim(n)] = v
        return Extensions(d)

    def get(self, oid, default=None):
        """
        Get the value of an extension by I{oid}.
        Note: The I{oid} may contain (*) wildcards.
        @param oid: An OID that may contain (*) wildcards.
        @type oid: str|L{OID}
        @return: The value of the first extension matched.
        @rtype: str
        """
        ext = self.find(oid, 1)
        if ext:
            return ext[0][1]
        else:
            return default

    def find(self, oid, limit=0):
        """
        Find all extensions matching the I{oid}.
        Note: The I{oid} may contain (*) wildcards.
        @param oid: An OID that may contain (*) wildcards.
        @type oid: str|L{OID}
        @param limit: Limit the number returned, 0=unlimited
        @type limit: int
        @return: A list of matching items.
        @rtype: (OID, value)
        @see: OID.match()
        """
        ext = []
        if isinstance(oid, str):
            oid = OID(oid)
        keyset = sorted(self.keys())
        for k in keyset:
            v = self[k]
            if k.match(oid):
                ext.append((k, v))
            if limit and len(ext) == limit:
                break
        return ext

    def branch(self, root):
        """
        Find a subtree by matching the oid.
        @param root: An OID that may contain (*) wildcards.
        @type root: str|L{OID}
        @return: A subtree.
        @rtype: L{Extensions}
        """
        d = {}
        if isinstance(root, str):
            root = OID(root)
        if root[-1]:
            root = root.append('')
        ln = len(root)-1
        for oid,v in self.find(root):
            trimmed = oid.ltrim(ln)
            d[trimmed] = v
        return Extensions(d)

    def __ext(self, x509):
        # get extensions substring
        text = x509.as_text()
        start = text.find('extensions:')
        end = text.rfind('Signature Algorithm:')
        text = text[start:end]
        text = text.replace('.\n', '..')
        return [s.strip() for s in text.split('\n')]

    def __parse(self, x509):
        # parse the extensions section
        oid = None
        for entry in self.__ext(x509):
            if oid is not None:
                self[oid] = entry[2:]
                oid = None
                continue
            m = self.pattern.match(entry)
            if m is None:
                continue
            oid = OID(entry[:-1])

    def __str__(self):
        s = []
        for item in self.items():
            s.append('%s = "%s"' % item)
        return '\n'.join(s)


class OID(object):
    """
    The Object Identifier object.
    @ivar part: The oid parts.
    @type part: [str,]
    @cvar WILDCARD: The wildcard character.
    @type WILDCARD: str
    """

    WILDCARD = '*'

    @classmethod
    def join(cls, *oid):
        return '.'.join(oid)

    @classmethod
    def split(cls, s):
        """
        Split an OID string.
        @param s: An OID string Eg: (1.2.3)
        @type s: str
        @return: A list of OID parts.
        @rtype: [str,]
        """
        return s.split('.')

    def __init__(self, oid):
        """
        @param oid: The OID value.
        @type oid: str|[str,]
        """
        if isinstance(oid, str):
            self.part = self.split(oid)
        else:
            self.part = oid

    def parent(self):
        """
        Get the parent OID.
        @return: The parent OID.
        @rtype: L{OID}
        """
        p = self.part[:-1]
        if p:
            return OID(p)

    def ltrim(self, n):
        """
        Left trim I{n} parts.
        @param n: The number of parts to trim.
        @type n: int
        @return: The trimmed OID
        @rtype: L{OID}
        """
        return OID(self.part[n:])

    def rtrim(self, n):
        """
        Right trim I{n} parts.
        @param n: The number of parts to trim.
        @type n: int
        @return: The trimmed OID
        @rtype: L{OID}
        """
        return OID(self.part[:-n])

    def append(self, oid):
        """
        Append the specified OID fragment.
        @param oid: An OID fragment.
        @type oid: str|L{OID}
        @return: The concatenated OID.
        @rtype: L{OID}
        """
        if isinstance(oid, str):
            oid = OID(oid)
        part = self.part + oid.part
        return OID(part)

    def match(self, oid):
        """
        Match the specified OID considering wildcards.
        Patterns:
          - 1.4.5.6.74 (not wildcarded)
          -    .5.6.74 (match on only last 4)
          -    5.6.74. (match only first 4)
          - 1.4.*.6.*  (wildcard pattern)
        @param oid: An OID string or object.
        @type oid: str|L{OID}
        @return: True if matched
        """
        i = 0
        if isinstance(oid, str):
            oid = OID(oid)
        try:
            if not oid[0]:
                oid = OID(oid[1:])
                parts = self.part[-len(oid):]
            elif not oid[-1]:
                oid = OID(oid[:-1])
                parts = self.part[:len(oid)]
            else:
                parts = self.part
            if len(parts) != len(oid):
                raise Exception()
            for x in parts:
                if ( x == oid[i] or oid[i] == self.WILDCARD ):
                    i += 1
                else:
                    raise Exception()
        except:
            return False
        return True

    def __len__(self):
        return len(self.part)

    def __getitem__(self, index):
        return self.part[index]

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return ( str(self) == str(other) )

    def __str__(self):
        return '.'.join(self.part)


class RedhatCertificate(Certificate):
    """
    Represents a Red Hat certificate.
    @cvar REDHAT: The Red Hat base OID.
    @type REDHAT: str
    """

    REDHAT = '1.3.6.1.4.1.2312.9'

    def update(self, content):
        Certificate.update(self, content)
        redhat = OID(self.REDHAT)
        n = len(redhat)
        self.__redhat = self.extensions().ltrim(n)

    def redhat(self):
        """
        Get the extension subtree for the B{redhat} namespace.
        @return: The extensions with the RH namespace trimmed.
        @rtype: L{Extension}
        """
        try:
            return self.__redhat
        except:
            return self.extensions()

    def bogus(self):
        bogus = Certificate.bogus(self)
        if self.serialNumber() < 1:
            bogus.append('Serial Number must be > 0')
        cn = self.subject().get('CN')
        if not cn:
            bogus.append('Common Name (%s) not-valid' % cn)
        return bogus


class ProductCertificate(RedhatCertificate):
    """
    Represents a Red Hat product/entitlement certificate.
    It is OID schema aware and provides methods to
    get product information.
    """

    def getProduct(self):
        """
        Get the product defined in the certificate.
        @return: A product object.
        @rtype: L{Product}
        """
        rhns = self.redhat()
        products = rhns.find('1.*.1', 1)
        if products:
            p = products[0]
            oid = p[0]
            root = oid.rtrim(1)
            hash = oid[1]
            ext = rhns.branch(root)
            return Product(hash, ext)

    def getProducts(self):
        """
        Get a list products defined in the certificate.
        @return: A list of product objects.
        @rtype: [L{Product},..]
        """
        lst = []
        rhns = self.redhat()
        for p in rhns.find('1.*.1'):
            oid = p[0]
            root = oid.rtrim(1)
            hash = oid[1]
            ext = rhns.branch(root)
            lst.append(Product(hash, ext))
        return lst

    def bogus(self):
        bogus = RedhatCertificate.bogus(self)
        if self.getProduct() is None:
            bogus.append('No product information')
        return bogus

    def __str__(self):
        s = []
        s.append('RAW:')
        s.append('===================================')
        s.append(Certificate.__str__(self))
        s.append('MODEL:')
        s.append('===================================')
        s.append('Serial#: %s' % self.serialNumber())
        s.append('Subject (CN): %s' % self.subject().get('CN'))
        s.append('Valid: [%s] %s\n' % (self.valid(), self.validRange()))
        for p in self.getProducts():
            s.append(str(p))
        return '\n'.join(s)


class EntitlementCertificate(ProductCertificate):
    """
    Represents an entitlement certificate.
    """

    def getOrder(self):
        """
        Get the B{order} object defined in the certificate.
        @return: An order object.
        @rtype: L{Order}
        """
        rhns = self.redhat()
        order = rhns.find('4.1', 1)
        if order:
            p = order[0]
            oid = p[0]
            root = oid.rtrim(1)
            ext = rhns.branch(root)
            return Order(ext)

    def getEntitlements(self):
        """
        Get the B{all} entitlements defined in the certificate.
        @return: A list of entitlement object.
        @rtype: [L{Entitlement},..]
        """
        return self.getContentEntitlements() \
             + self.getRoleEntitlements()

    def getContentEntitlements(self):
        """
        Get the B{content} entitlements defined in the certificate.
        @return: A list of entitlement object.
        @rtype: [L{Content},..]
        """
        lst = []
        rhns = self.redhat()
        entitlements = rhns.find('2.*.1.1')
        for ent in entitlements:
            oid = ent[0]
            root = oid.rtrim(1)
            ext = rhns.branch(root)
            lst.append(Content(ext))
        return lst

    def getRoleEntitlements(self):
        """
        Get the B{role} entitlements defined in the certificate.
        @return: A list of entitlement object.
        @rtype: [L{Role},..]
        """
        lst = []
        rhns = self.redhat()
        entitlements = rhns.find('3.*.1')
        for ent in entitlements:
            oid = ent[0]
            root = oid.rtrim(1)
            ext = rhns.branch(root)
            lst.append(Role(ext))
        return lst

    def bogus(self):
        bogus = ProductCertificate.bogus(self)
        if self.getOrder() is None:
            bogus.append('No order infomation')
        return bogus

    def __str__(self):
        s = []
        order = self.getOrder()
        s.append(ProductCertificate.__str__(self))
        for ent in self.getEntitlements():
            s.append(str(ent))
        s.append(str(order))
        return '\n'.join(s)


class Order:

    def __init__(self, ext):
        self.ext = ext

    def getName(self):
        return self.ext.get('1')

    def getNumber(self):
        return self.ext.get('2')

    def getSku(self):
        return self.ext.get('3')

    def getSubscription(self):
        return self.ext.get('4')

    def getQuantity(self):
        return self.ext.get('5')

    def getStart(self):
        return self.ext.get('6')

    def getEnd(self):
        return self.ext.get('7')

    def getSubtype(self):
        return self.ext.get('8')

    def getVirtLimit(self):
        return self.ext.get('9')

    def getSocketLimit(self):
        return self.ext.get('10')

    def getOptionCode(self):
        return self.ext.get('11')

    def getContract(self):
        return self.ext.get('12')

    def __str__(self):
        s = []
        s.append('Order {')
        s.append('\tName .......... = %s' % self.getName())
        s.append('\tNumber ........ = %s' % self.getNumber())
        s.append('\tSKU ........... = %s' % self.getSku())
        s.append('\tSubscription .. = %s' % self.getSubscription())
        s.append('\tQuantity ...... = %s' % self.getQuantity())
        s.append('\tStart (Ent) ... = %s' % self.getStart())
        s.append('\tEnd (Ent) ..... = %s' % self.getEnd())
        s.append('\tSubtype ....... = %s' % self.getSubtype())
        s.append('\tVirt Limit .... = %s' % self.getVirtLimit())
        s.append('\tSocket Limit .. = %s' % self.getSocketLimit())
        s.append('\tOption Code ... = %s' % self.getOptionCode())
        s.append('\tContract ...... = %s' % self.getContract())
        s.append('}')
        return '\n'.join(s)


class Product:

    def __init__(self, hash, ext):
        self.hash = hash
        self.ext = ext

    def getHash(self):
        return self.hash

    def getName(self):
        return self.ext.get('1')

    def getVariant(self):
        return self.ext.get('2')

    def getArch(self):
        return self.ext.get('3')

    def getVersion(self):
        return self.ext.get('4')

    def __eq__(self, rhs):
        return ( self.getHash() == rhs.getHash() )

    def __str__(self):
        s = []
        s.append('Product {')
        s.append('\tHash ......... = %s' % self.getHash())
        s.append('\tName ......... = %s' % self.getName())
        s.append('\tVariant ...... = %s' % self.getVariant())
        s.append('\tArchitecture . = %s' % self.getArch())
        s.append('\tVersion ...... = %s' % self.getVersion())
        s.append('}')
        return '\n'.join(s)

    def __repr__(self):
        return str(self)


class Entitlement:

    def __init__(self, ext):
        self.ext = ext


class Content(Entitlement):

    def getName(self):
        return self.ext.get('1')

    def getLabel(self):
        return self.ext.get('2')

    def getQuantity(self):
        return self.ext.get('3')

    def getFlexQuantity(self):
        return self.ext.get('4')

    def getVendor(self):
        return self.ext.get('5')

    def getUrl(self):
        return self.ext.get('6')

    def getGpg(self):
        return self.ext.get('7')

    def getEnabled(self):
        return self.ext.get('8')

    def __eq__(self, rhs):
        return ( self.getLabel() == rhs.getLabel() )

    def __str__(self):
        s = []
        s.append('Entitlement (content) {')
        s.append('\tName ........ = %s' % self.getName())
        s.append('\tLabel ....... = %s' % self.getLabel())
        s.append('\tQuantity .... = %s' % self.getQuantity())
        s.append('\tFlex Quantity = %s' % self.getFlexQuantity())
        s.append('\tVendor ...... = %s' % self.getVendor())
        s.append('\tURL ......... = %s' % self.getUrl())
        s.append('\tGPG Key ..... = %s' % self.getGpg())
        s.append('\tEnabled ..... = %s' % self.getEnabled())
        s.append('}')
        return '\n'.join(s)

    def __repr__(self):
        return str(self)


class Role(Entitlement):

    def getName(self):
        return self.ext.get('1')

    def getDescription(self):
        return self.ext.get('2')

    def __eq__(self, rhs):
        return ( self.getName() == rhs.getName() )

    def __str__(self):
        s = []
        s.append('Entitlement (role) {')
        s.append('\tName ......... = %s' % self.getName())
        s.append('\tDescription .. = %s' % self.getDescription())
        s.append('}')
        return '\n'.join(s)

    def __repr__(self):
        return str(self)


class Bundle(object):

    KEY_PATTERN = re.compile(
        '-----BEGIN.+KEY-----\n.+\n-----END.+KEY-----',
        re.DOTALL)
    CERT_PATTERN = re.compile(
        '-----BEGIN CERTIFICATE-----\n.+\n-----END CERTIFICATE-----',
        re.DOTALL)

    @classmethod
    def split(cls, pem):
        m = cls.KEY_PATTERN.search(pem)
        if m is None:
            raise Exception, 'Key not found.'
        key = m.group(0)
        m = cls.CERT_PATTERN.search(pem)
        if m is None:
            raise Exception, 'Certificate not found.'
        cert = m.group(0)
        return (key, cert)

    def __init__(self, key=None, cert=None):
        self.key = key
        self.cert = cert

    def read(self, path):
        f = open(path)
        try:
            b = self.split(f.read())
            self.key = b[0]
            self.cert = b[1]
            self.path = path
        finally:
            f.close()
        return self

    def write(self, path):
        f = open(path, 'w')
        try:
            f.write(str(self))
            self.path = path
        finally:
            f.close()
        return self

    def __str__(self):
        s = []
        s.append(self.key)
        s.append(self.cert)
        s.append('')
        return '\n'.join(s)


import sys
if __name__ == '__main__':
    for path in sys.argv[1:]:
        print path
        pc = EntitlementCertificate()
        pc.read(path)
        print pc
