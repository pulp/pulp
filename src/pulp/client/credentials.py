# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Module containing classes to manage client credentials.
"""

import os
import re
from pulp.client.config import Config
from gettext import gettext as _
from M2Crypto import X509
from logging import getLogger

log = getLogger(__name__)

cfg = Config()


class Bundle:
    """
    Represents x509, pem encoded key & certificate bundles.
    It works with separate key and certificate file and/or
    consolidated files.
    """

    KEY_PATTERN = re.compile(r'[\-]{5}BEGIN (RSA|DSA) PRIVATE KEY[\-]{5}')
    CRT_PATTERN = re.compile(r'[\-]{5}BEGIN CERTIFICATE[\-]{5}')
    
    @classmethod
    def haskey(cls, s):
        """
        Get whether the string contains a PEM encoded private key.
        @param s: A PEM string.
        @type s: str
        @return: True if contains a key.
        @rtype: bool
        """
        m = cls.KEY_PATTERN.search(s)
        return ( m is not None )

    @classmethod
    def hascrt(cls, s):
        """
        Get whether the string contains a PEM encoded certificate.
        @param s: A PEM string.
        @type s: str
        @return: True if contains a certificate.
        @rtype: bool
        """
        m = cls.CRT_PATTERN.search(s)
        return ( m is not None )

    @classmethod
    def hasboth(cls, s):
        """
        Get whether the string contains both
          a PEM encoded private key AND certificate.
        @param s: A PEM string.
        @type s: str
        @return: True if contains a key & cert.
        @rtype: bool
        """
        return ( cls.haskey(s) and cls.hascrt(s) )

    def root(self):
        """
        Get the bundle I{root} directory.
        @return: An absolute path.
        @rtype: str
        """
        pass

    def crtpath(self):
        """
        Get the absolute path to the certificate file.
        @return: Absolute path to certificate.
        @rtype: str
        """
        pass

    def valid(self):
        """
        Validate the bundle.
        @return: True if exists & valid.
        @rtype: bool
        """
        s = self.read()
        return self.hasboth(s)

    def read(self):
        """
        Read and return the bundle contents.
        @return: A string containing the PEM encoded key & cert.
        @rtype: str
        """
        f = open(self.crtpath())
        content = f.read()
        f.close()
        return content

    def write(self, content):
        """
        Write the specified bundle content.
        @param content: The PEM text for the private key and certificate.
        @type content: str
        """
        self.mkdir()
        f = open(self.crtpath(), 'w')
        f.write(content)
        f.close()

    def delete(self):
        """
        Delete the certificate.
        """
        path = self.crtpath()
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except IOError:
            log.error(path, exc_info=1)

    def mkdir(self):
        """
        Ensure I{root} directory exists.
        """
        path = self.root()
        if not os.path.exists(path):
            os.makedirs(path)

    def __str__(self):
        return 'bundle: %s' % repr(self.keypath(), self.crtpath())


class Login(Bundle):
    """
    The bundle for logged in user.
    """

    ROOT = '~/.pulp'
    KEY = 'user-key.pem'
    CRT = 'user-cert.pem'

    def root(self):
        return os.path.expanduser(self.ROOT)

    def crtpath(self):
        return os.path.join(self.root(), self.CRT)


class Consumer(Bundle):
    """
    The bundle for the consumer.
    """

    ROOT = '/etc/pki/consumer'
    KEY = 'key.pem'
    CRT = 'cert.pem'

    def root(self):
        return self.ROOT

    def crtpath(self):
        return os.path.join(self.root(), self.CRT)

    def getid(self):
        """
        Get the consumer ID.
        @return: The consumer ID.
        @rtype: str
        """
        if self.valid():
            content = self.read()
            x509 = X509.load_cert_string(content)
            subject = self.subject(x509)
            return subject['CN']

    def subject(self, x509):
        """
        Get the certificate subject.
        note: Missing NID mapping for UID added to patch openssl.
        @return: A dictionary of subject fields.
        @rtype: dict
        """
        d = {}
        subject = x509.get_subject()
        subject.nid['UID'] = 458
        for key, nid in subject.nid.items():
            entry = subject.get_entries_by_nid(nid)
            if len(entry):
                asn1 = entry[0].get_data()
                d[key] = str(asn1)
                continue
        return d
