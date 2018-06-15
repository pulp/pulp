import logging
import subprocess
import uuid

from M2Crypto import X509, EVP, RSA, util

from pulp.common.util import encode_unicode
from pulp.server import config
from pulp.server.exceptions import PulpException
from pulp.server.util import Singleton


_logger = logging.getLogger(__name__)

ADMIN_PREFIX = 'admin:'
ADMIN_SPLITTER = ':'


class CertGenerationManager(object):
    def make_admin_user_cert(self, user):
        """
        Generates a x509 certificate for an admin user.

        :param user: identification the certificate will be created for; may not be None
        :type  user: pulp.server.db.model.User

        :return: tuple of PEM encoded private key and certificate
        :rtype:  (str, str)
        """
        expiration = config.config.getint('security', 'user_cert_expiration')
        return self.make_cert(self.encode_admin_user(user), expiration)

    def make_cert(self, cn, expiration, uid=None):
        """
        Generate an x509 certificate with the Subject set to the cn passed into this method:
        Subject: CN=someconsumer.example.com

        :param cn: ID to be embedded in the certificate
        :type  cn: string

        :param uid: The optional userid.  In pulp, this is the DB document _id
            for both users and consumers.
        :type uid: str

        :return: tuple of PEM encoded private key and certificate
        :rtype:  (str, str)
        """
        # Ensure we are dealing with a string and not unicode
        try:
            cn = str(cn)
        except UnicodeEncodeError:
            cn = encode_unicode(cn)

        _logger.debug("make_cert: [%s]" % cn)

        # Make a private key
        # Don't use M2Crypto directly as it leads to segfaults when trying to convert
        # the key to a PEM string.  Instead create the key with openssl and return the PEM string
        # Sorta hacky but necessary.
        # rsa = RSA.gen_key(1024, 65537, callback=passphrase_callback)
        private_key_pem = _make_priv_key()
        rsa = RSA.load_key_string(private_key_pem,
                                  callback=util.no_passphrase_callback)

        # Make the Cert Request
        req, pub_key = _make_cert_request(cn, rsa, uid=uid)

        # Sign it with the Pulp server CA
        # We can't do this in m2crypto either so we have to shell out

        ca_cert = config.config.get('security', 'cacert')
        ca_key = config.config.get('security', 'cakey')

        sn = SerialNumber()
        serial = sn.getSerialNumber()

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

    def verify_cert(self, cert_pem):
        '''
        Ensures the given certificate can be verified against the server's CA.

        :param cert_pem: PEM encoded certificate to be verified
        :type  cert_pem: string

        :return: True if the certificate is successfully verified against the CA; False otherwise
        :rtype:  boolean
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

    def encode_admin_user(self, user):
        '''
        Encodes an admin user's identity into a single line suitable for identification.
        This is intended to be the identity used in admin certificates.

        :param user: admin user; may not be None
        :type user:  pulp.server.db.model.User

        :return: single line identification of the admin user safe for public visibility;
                 any sensitive information is hashed
        :rtype:  string
        '''
        return '%s%s%s%s' % (ADMIN_PREFIX, user.login, ADMIN_SPLITTER, str(user.id))

    def decode_admin_user(self, encoded_string):
        '''
        Decodes the single line admin user identification produced by encode_admin_user
        into all of the parts that make up that identification.

        :param encoded_string: string representation of the user provided by encode_admin_user
        :type  encoded_string: string

        :return: tuple of information describing the admin user; (username, id)
        :rtype:  (string, string)
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


class SerialNumber:

    __metaclass__ = Singleton

    def getSerialNumber(self):
        """
        Returns a uuid to use for the next serial number.

        x509 standards indicate that serial number must be unique, not that it must be
        monotonically increasing. By using a uuid the chance of collision is very low.

        :return: A serial number
        :rtype: int
        """

        return int(uuid.uuid4())


def _make_priv_key():
    cmd = 'openssl genrsa 1024'
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    exit_code = p.returncode
    error = p.stderr.read()
    if exit_code != 0:
        raise Exception("error generating private key: %s" % error)
    output = p.stdout.read()
    try:
        start_index = output.index("-----BEGIN RSA PRIVATE KEY-----")
    except ValueError:
        # OpenSSL does not support RSA in FIPS mode
        start_index = output.index("-----BEGIN PRIVATE KEY-----")
    pem_str = output[start_index:]
    return pem_str


def _make_cert_request(cn, rsa, uid=None):
    pub_key = EVP.PKey()
    request = X509.Request()
    pub_key.assign_rsa(rsa)
    request.set_pubkey(pub_key)
    subject = request.get_subject()
    subject.nid['UID'] = 458  # openssl lacks support for userid
    subject.CN = "%s" % cn
    if uid:
        subject.UID = uid
    ext2 = X509.new_extension('nsComment', 'Pulp Identity Certificate for Consumer: [%s]' % cn)
    extensions = X509.X509_Extension_Stack()
    extensions.push(ext2)
    request.add_extensions(extensions)
    request.sign(pub_key, 'sha256')
    return request, pub_key
