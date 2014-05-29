# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from M2Crypto import RSA, BIO
from gofer.messaging.auth import ValidationFailed

from pulp.server.config import config as pulp_conf
from pulp.server.managers import factory as managers
from pulp.server.exceptions import MissingResource
from pulp.common.config import parse_bool


class Authenticator(object):
    """
    Provides message authentication using RSA keys.
    The server and the agent sign sent messages using their private keys
    and validate received messages using each others public keys.
    :ivar enabled: Signing and validation are enabled.
    :type enabled: bool
    :ivar rsa_key: The private RSA key used for signing.
    :type rsa_key: RSA.RSA
    """

    def __init__(self):
        self.rsa_key = None
        self.enabled = parse_bool(pulp_conf.get('messaging', 'auth_enabled'))

    def load(self):
        """
        Load the private key.
        """
        path = pulp_conf.get('authentication', 'rsa_key')
        with open(path) as fp:
            pem = fp.read()
            bfr = BIO.MemoryBuffer(pem)
            self.rsa_key = RSA.load_key_bio(bfr)

    @staticmethod
    def get_key(consumer_id):
        """
        Get the consumer's public RSA key.
        :return: The consumer's public RSA key.
        :rtype: RSA.RSA
        """
        rsa_pub = 'rsa_pub'
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id, fields=[rsa_pub])
        pem = consumer[rsa_pub]
        bfr = BIO.MemoryBuffer(str(pem))
        return RSA.load_pub_key_bio(bfr)

    def sign(self, digest):
        """
        Sign the specified message.
        :param digest: A message digest.
        :type digest: str
        :return: The message signature.
        :rtype: str
        """
        if self.enabled:
            return self.rsa_key.sign(digest)
        else:
            return ''

    def validate(self, document, digest, signature):
        """
        Validate the specified message and signature.
        :param document: The original signed document.
        :type document: gofer.messaging.Document
        :param digest: A message digest.
        :type digest: str
        :param signature: A message signature.
        :type signature: str
        :raises ValidationFailed: when message is not valid.
        """
        if not self.enabled:
            return
        try:
            consumer_id = document.any['consumer_id']
            key = self.get_key(consumer_id)
            if not key.verify(digest, signature):
                raise ValidationFailed()
        except (MissingResource, RSA.RSAError):
            raise ValidationFailed()
