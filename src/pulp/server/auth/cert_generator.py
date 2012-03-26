# -*- coding: utf-8 -*-
#
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

import logging
import fcntl
from M2Crypto import X509, EVP, RSA, util
from threading import RLock
import subprocess

from pulp.server.exceptions import PulpException
from pulp.server import config
from pulp.server.util import Singleton
from pulp.common.util import encode_unicode

log = logging.getLogger(__name__)

ADMIN_PREFIX = 'admin:'
ADMIN_SPLITTER = ':'


class SerialNumber:

    PATH = '/var/lib/pulp/sn.dat'
    __mutex = RLock()
    __metaclass__ = Singleton

    def next(self):
        """
        Get the next serial#
        @return: The next serial#
        @rtype: int
        """
        self.__mutex.acquire()
        try:
            fp = open(self.PATH, 'a+')
            try:
                sn = int(fp.read()) + 1
            except:
                sn = 1
            fp.seek(0)
            fp.truncate(0)
            fp.write(str(sn))
            fp.close()
            return sn
        finally:
            self.__mutex.release()

    def reset(self):
        """
        Reset the serial number
        """
        self.__mutex.acquire()
        try:
            fp = open(self.PATH, 'w')
            fp.write('0')
            fp.close()
        finally:
            self.__mutex.release()


def make_admin_user_cert(user):
    '''
    Generates a x509 certificate for an admin user.

    @param user: identification the certificate will be created for; may not be None
    @type  user: pulp.server.db.model.User

    @return: tuple of PEM encoded private key and certificate
    @rtype:  (str, str)
    '''
    expiration = config.config.getint('security', 'user_cert_expiration')
    return make_cert(encode_admin_user(user), expiration)

def make_cert(uid, expiration):
    """
    Generate an x509 certificate with the Subject set to the uid passed into this method:
    Subject: CN=someconsumer.example.com
    
    @param uid: ID to be embedded in the certificate
    @type  uid: string

    @return: tuple of PEM encoded private key and certificate
    @rtype:  (str, str)
    """
    # Ensure we are dealing with a string and not unicode
    try:
        uid = str(uid)
    except UnicodeEncodeError:
        uid = encode_unicode(uid)

    log.debug("make_cert: [%s]" % uid)
    
    #Make a private key
    # Don't use M2Crypto directly as it leads to segfaults when trying to convert
    # the key to a PEM string.  Instead create the key with openssl and return the PEM string
    # Sorta hacky but necessary.
    # rsa = RSA.gen_key(1024, 65537, callback=passphrase_callback)
    private_key_pem = _make_priv_key()
    rsa = RSA.load_key_string(private_key_pem,
                              callback=util.no_passphrase_callback)
    
    # Make the Cert Request
    req, pub_key = _make_cert_request(uid, rsa)

    # Sign it with the Pulp server CA
    # We can't do this in m2crypto either so we have to shell out
    
    ca_cert = config.config.get('security', 'cacert')
    ca_key = config.config.get('security', 'cakey')

    sn = SerialNumber()
    serial = sn.next()

    cmd = 'openssl x509 -req -sha1 -CA %s -CAkey %s -set_serial %s -days %d' % \
          (ca_cert, ca_key, serial, expiration)
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, 
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = p.communicate(input=req.as_pem())[0]
    p.wait()
    exit_code = p.returncode
    if exit_code != 0:
        raise Exception("error signing cert request: %s" % output)
    cert_pem_string = output[output.index("-----BEGIN CERTIFICATE-----"):]
    return private_key_pem, cert_pem_string

def verify_cert(cert_pem):
    '''
    Ensures the given certificate can be verified against the server's CA.

    @param cert_pem: PEM encoded certificate to be verified
    @type  cert_pem: string

    @return: True if the certificate is successfully verified against the CA; False otherwise
    @rtype:  boolean
    '''

    # M2Crypto doesn't support verifying a cert against a CA, so call out to openssl
    ca_cert = config.config.get('security', 'cacert')
    cmd = 'openssl verify -CAfile %s' % ca_cert
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Use communicate to pipe the certificate to the verify call
    stdout, stderr = p.communicate(input=cert_pem)

    # Successful result example:
    #   stdin: OK\n
    # Failed result example:
    #   stdin: C = US, ST = NC, L = Raleigh, O = Red Hat, CN = localhost
    #   error 20 at 0 depth lookup:unable to get local issuer certificate\n
    result = stdout.rstrip()

    if result.endswith('OK'):
        return True
    else:
        return False

def encode_admin_user(user):
    '''
    Encodes an admin user's identity into a single line suitable for identification.
    This is intended to be the identity used in admin certificates.

    @param user: admin user; may not be None
    @type user:  pulp.server.db.model.User

    @return: single line identification of the admin user safe for public visibility;
             any sensitive information is hashed
    @rtype:  string
    '''
    return '%s%s%s%s' % (ADMIN_PREFIX, user['login'], ADMIN_SPLITTER, user['id'])

def is_admin_user(encoded_string):
    '''
    Indicates if the encoded user string represents an admin user. If the string is
    identified as an admin user, it can be parsed with decode_admin_user.

    @return: True if the user string represents an admin user; False otherwise
    @rtype:  boolean
    '''
    return encoded_string.startswith(ADMIN_PREFIX)

def decode_admin_user(encoded_string):
    '''
    Decodes the single line admin user identification produced by encode_admin_user
    into all of the parts that make up that identification.

    @param encoded_string: string representation of the user provided by encode_admin_user
    @type  encoded_string: string

    @return: tuple of information describing the admin user; (username, id)
    @rtype:  (string, string)
    '''

    # Strip off the leading "admin:" prefix
    encoded_string = encoded_string[len(ADMIN_PREFIX):]

    # Find where to split
    parsed = encoded_string.split(ADMIN_SPLITTER)

    if len(parsed) != 2:
        raise PulpException('Invalid encoded admin user information [%s]' % encoded_string)

    username = parsed[0]
    id = parsed[1]

    return username, id

def _make_priv_key():
    cmd = 'openssl genrsa 1024'
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    exit_code = p.returncode
    error = p.stderr.read()
    if exit_code != 0:
        raise Exception("error generating private key: %s" % error)
    output = p.stdout.read()
    pem_str = output[output.index("-----BEGIN RSA PRIVATE KEY-----"):]
    return pem_str
    

def _make_cert_request(uid, rsa):
    pub_key = EVP.PKey()
    x = X509.Request()
    pub_key.assign_rsa(rsa)
    rsa = None # should not be freed here
    x.set_pubkey(pub_key)
    name = x.get_subject()
    name.CN = "%s" % uid
    ext2 = X509.new_extension('nsComment', 
        'Pulp Generated Identity Certificate for Consumer: [%s]' % uid)
    extstack = X509.X509_Extension_Stack()
    extstack.push(ext2)
    x.add_extensions(extstack)
    x.sign(pub_key,'sha1')
    pk2 = x.get_pubkey()
    return x, pub_key

