# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import re
from M2Crypto import X509


EXMSG = \
"""
A bundle must contain both the private key and
certificate PEM text.  The [%s] PEM text was not found.
"""
EXMSG_AT_PATH = \
"""
The bundle at: %s
must contain both the private key and certificate
PEM text.  The [%s] PEM text was not found.
"""


class KeyNotFound(Exception):

    def __init__(self, bundle, path=None):
        if path:
            msg = EXMSG_AT_PATH % (path, 'key')
        else:
            msg = EXMSG % 'key'
        Exception.__init__(self, msg)


class CertNotFound(Exception):

    def __init__(self, bundle, path=None):
        if path:
            msg = EXMSG_AT_PATH % (path, 'certificate')
        else:
            msg = EXMSG % 'certificate'
        Exception.__init__(self, msg)


class Bundle:
    """
    Represents x509, pem encoded key & certificate bundles.
    """

    KEY_BEGIN = re.compile(r'[\n]*[\-]{5}BEGIN( RSA| DSA)? PRIVATE KEY[\-]{5}')
    KEY_END = re.compile(r'[\-]{5}END( RSA| DSA)? PRIVATE KEY[\-]{5}')
    CRT_BEGIN = re.compile(r'[\n]*[\-]{5}BEGIN CERTIFICATE[\-]{5}')
    CRT_END = re.compile(r'[\-]{5}END CERTIFICATE[\-]{5}')
    
    @classmethod
    def haskey(cls, bundle):
        """
        Get whether the string contains a PEM encoded private key.
        @param bundle: A PEM string.
        @type bundle: str
        @return: True if contains a key.
        @rtype: bool
        """
        m = cls.KEY_BEGIN.search(bundle)
        return ( m is not None )

    @classmethod
    def hascrt(cls, bundle):
        """
        Get whether the string contains a PEM encoded certificate.
        @param bundle: A PEM string.
        @type bundle: str
        @return: True if contains a certificate.
        @rtype: bool
        """
        m = cls.CRT_BEGIN.search(bundle)
        return ( m is not None )

    @classmethod
    def hasboth(cls, bundle):
        """
        Get whether the string contains both
          a PEM encoded private key AND certificate.
        @param bundle: A PEM string.
        @type bundle: str
        @return: True if contains a key & cert.
        @rtype: bool
        """
        return ( cls.haskey(bundle) and cls.hascrt(bundle) )
    
    @classmethod
    def assertvalid(cls, bundle, path=None):
        """
        Validate that the bundle is valid.
        @param bundle: A bundle to validate.
        @type bundle: str
        @raise KeyMissing: When key PEM is missing.
        @raise CertMissing: When cert PEM is missing.
        """
        if not cls.haskey(bundle):
            raise KeyNotFound(bundle, path)
        if not cls.hascrt(bundle):
            raise CertNotFound(bundle, path)

    @classmethod
    def split(cls, bundle):
        """
        Split the bundle into key and certificate components.
        @param bundle: A bundle containing the key and certificate PEM.
        @type bundle: str
        @return: (key,crt)
        @rtype: tuple
        """
        # key
        begin = cls.KEY_BEGIN.search(bundle)
        end = cls.KEY_END.search(bundle)
        if not (begin and end):
            raise Exception, '%s, not valid' % bundle
        begin = begin.start(0)
        end = end.end(0)
        key = bundle[begin:end]
        # certificate
        begin = cls.CRT_BEGIN.search(bundle)
        end = cls.CRT_END.search(bundle)
        if not (begin and end):
            raise Exception, '%s, not valid' % bundle
        begin = begin.start(0)
        end = end.end(0)
        crt= bundle[begin:end]
        return (key.strip(), crt.strip())

    @classmethod
    def join(cls, key, crt):
        """
        Join the specified key and certificate not a bundle.
        @param key: A private key (PEM).
        @type key: str
        @param crt: A certificate (PEM).
        @type crt: str
        @return: A bundle containing the key and certifiate.
        @rtype: str
        """
        key = key.strip()
        crt = crt.strip()
        return '\n'.join((key, crt))
    
    def __init__(self, path):
        """
        @param path: The absolute path to the bundle represented.
        @type path: str
        """
        self.path = os.path.expanduser(path)

    def valid(self):
        """
        Validate the bundle.
        @return: True if exists & valid.
        @rtype: bool
        """
        if os.path.exists(self.path):
            s = self.read()
            return self.hasboth(s)
        else:
            return False

    def read(self):
        """
        Read and return the bundle contents.
        @return: A string containing the PEM encoded key & cert.
        @rtype: str
        """
        f = open(self.path)
        bundle = f.read()
        f.close()
        self.assertvalid(bundle, self.path)
        return bundle

    def write(self, bundle):
        """
        Write the specified bundle content.
        @param bundle: The PEM text for the private key and certificate.
        @type bundle: str
        """
        self.mkdir()
        self.assertvalid(bundle)
        f = open(self.path, 'w')
        f.write(bundle)
        f.close()

    def delete(self):
        """
        Delete the certificate.
        """
        try:
            if os.path.exists(self.path):
                os.unlink(self.path)
        except IOError:
            log.error(path, exc_info=1)

    def mkdir(self):
        """
        Ensure I{root} directory exists.
        """
        path = os.path.dirname(self.path)
        if not os.path.exists(path):
            os.makedirs(path)

    def cn(self):
        """
        Get the subject (CN) Common Name
        @return: The subject CN
        @rtype: str
        """
        if self.valid():
            subject = self.subject()
            return subject['CN']

    def subject(self):
        """
        Get the certificate subject.
        note: Missing NID mapping for UID added to patch openssl.
        @return: A dictionary of subject fields.
        @rtype: dict
        """
        d = {}
        content = self.read()
        x509 = X509.load_cert_string(content)
        subject = x509.get_subject()
        subject.nid['UID'] = 458
        for key, nid in subject.nid.items():
            entry = subject.get_entries_by_nid(nid)
            if len(entry):
                asn1 = entry[0].get_data()
                d[key] = str(asn1)
                continue
        return d

    def __str__(self):
        return 'bundle: %s' % self.path
