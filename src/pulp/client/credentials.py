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
import hashlib
from pulp.client.config import Config
from gettext import gettext as _
from M2Crypto import X509

cfg = Config()


class CredentialError(Exception):
    """
    Credentials fail to validate
    """
    pass


class Bundle:
    """
    Represents x509, pem encoded key & cert bundles.
    """

    def root(self):
        """
        Get the bundle I{root} directory.
        @return: An absolute path.
        @rtype: str
        """
        pass

    def keypath(self):
        """
        Get the absolute path to the private key file.
        @return: Absolute path to the private key.
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
        validkey = os.path.exists(self.keypath())
        validcrt = os.path.exists(self.crtpath())
        return ( validkey and validcrt )

    def read(self):
        """
        Read and return the bundle contents.
        @return: A tuple containing the PEM encoded key & cert.
        @rtype: tuple
        """
        if self.valid():
            f = open(self.keypath(), 'r')
            key = f.read()
            f.close()
            f = open(self.crtpath(), 'r')
            crt = f.read()
            f.close()
        else:
            key = None
            crt = None
        return (key, crt)

    def digest(self):
        """
        Get a SHA-1 hex digest for the bundle contents.
        @return: hex digest
        @rtype: str
        """
        if not self.valid():
            return None
        sha = hashlib.sha256()
        for s in self.read():
            sha.update(s)
        return sha.hexdigest()


    def write(self, key, crt):
        """
        Write the specified I{key} & I{crt} bundle.
        @param key: The PEM text for the private key.
        @type key: str
        @param crt: The PEM text for the cert.
        @type crt: str
        """
        self.mkdir()
        f = open(self.keypath(), 'w')
        f.write(key)
        f.close()
        f = open(self.crtpath(), 'w')
        f.write(crt)
        f.close()

    def delete(self):
        """
        Delete the bundle.
        """
        for path in (self.keypath(), self.crtpath()):
            try:
                os.unlink(path)
            except:
                pass

    def mkdir(self):
        """
        Ensure I{root} directory exists.
        """
        path = self.root()
        if not os.path.exists(path):
            os.makedirs(path)


class Login(Bundle):
    """
    The bundle for logged in user.
    """

    ROOT = '~/.pulp'
    KEY = 'user-key.pem'
    CRT = 'user-cert.pem'

    def root(self):
        return os.path.expanduser(self.ROOT)

    def keypath(self):
        return os.path.join(self.root(), self.KEY)

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

    def keypath(self):
        return os.path.join(self.root(), self.KEY)

    def crtpath(self):
        return os.path.join(self.root(), self.CRT)

    def getid(self):
        """
        Get the consumer ID.
        @return: The consumer ID.
        @rtype: str
        """
        try:
            f = open(self.crtpath())
            content = f.read()
            f.close()
            x509 = X509.load_cert_string(content)
            subject = self.subject(x509)
            return subject['CN']
        except IOError:
            pass

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


class Manual:
    """
    A manually defined bundle.
    Usually passed as parameters to the CLI.
    """

    __keypath = None
    __crtpath = None

    @classmethod
    def set(self, key, crt):
        self.__keypath = key
        self.__crtpath = crt

    def keypath(self):
        return self.__keypath

    def crtpath(self):
        return self.__crtpath

    def valid(self):
        return ( self.__keypath and self.__crtpath )


class Credentials:
    """
    Represents the client credentials.
    """

    __userid = None
    __password = None
    __server   = None

    @classmethod
    def setuser(cls, userid=None, password=None):
        """
        Set the current logged in user credentials.
        @param userid: The user name.
        @type userid: str
        @param password: The password
        @type password: str
        """
        cls.__userid = userid
        cls.__password = password

    @classmethod
    def setcert(cls, keypath=None, crtpath=None):
        """
        Overrides certificate credentials.
        @param keypath: The abolute path to a private key.
        @type keypath: str
        @param crtpath: The absolute path to a cert.
        @type crtpath: str
        """
        Manual.set(keypath, crtpath)
        
    @classmethod    
    def setserver(cls, server=None):
        """
        Overrides certificate server url
        @param server: server url
        @type server: str
        """
        cls.__server = server 

    def best(self):
        """
        Get the best available credentials.
        @return: Tuple: (userid,pwd,keypath,crtpath)
        @rtype: tuple.
        """
        if not self.__userid or not self.__password:
            key, crt = self.__bestbundle()
        else:
            key, crt = (None, None)
        credentials = (self.__userid, self.__password, key, crt, self.__server)
        self.validate(credentials)
        return credentials

    def validate(self, credentials):
        """
        Validate credentials.
        Must have either valid userid/password OR valid key,crt.
        @raise CredentialsError: When credentials insufficient.
        """
        userid, password, key, crt, server = credentials
        if userid and password:
            return
        if key and crt:
            return
        raise CredentialError, _('No valid credentials found')

    def __bestbundle(self):
        for bclass in (Manual, Login, Consumer):
            b = bclass()
            if b.valid():
                return (b.keypath(), b.crtpath())
        return (None, None)
