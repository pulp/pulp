"""
Classes that provide URL signing and validation.
The approach is modeled after Amazon EC2 signing.

Example:

unsigned:

http://redhat.com/content/test.rpm

signed:

http://redhat.com/content/test.rpm?policy=eyJyZXNvdXJjZSI6ICIvY29udGVudC90ZXN0LnJwbSIsICJleHBpcmF0a
W9uIjogMTQ0MjkzMTc4OH0%3D;signature=PTgdjh0uq1lXDfpvAbYXxF_TO8BKHT4Eo6OYo6M45UL0jIokZ2P5s-tAclzAx-E
Lv3x7kfjAADA8Cpsk9iHBeeq3pKTX6Ogv_R-BkORxJAAzeM7et9M1HkyGKwBl8BTYAA3POQT0Ips4Zb0LN5uDHFPwclS-W1jvKD
095g__lhvLmiiVLw5biVM3WFvlUl0-hd4ljzbvB4qrXRGbNtw1rnbCIowM0h2_SsoS_WzetJWsiZNdMVySfUXKJ4m3-du89wWB7
zDFYRlosVNTom5YiKprVkJEAo3cbTOMoZss_NS-vpzauuk-qXwqj05gI7fJVsVD915gGcY0xPUbpCbVTg%3D%3D
"""

from base64 import urlsafe_b64encode, urlsafe_b64decode
from gettext import gettext as _
from hashlib import sha256
from time import time
from urllib import quote, unquote
from urlparse import ParseResult, urlparse, urlunparse

from M2Crypto import RSA, BIO

from pulp.server.compat import json


class NotValid(Exception):
    """
    URL or policy is not valid.
    """
    pass


class DecodingError(NotValid):
    """
    The json or base64 decoding is invalid.
    """

    DESCRIPTION = _('The JSON or base64 decoding failed: {r}.')

    def __init__(self, reason):
        super(DecodingError, self).__init__(self.DESCRIPTION.format(r=reason))


class NotSigned(NotValid):
    """
    The URL has not been signed.
    The POLICY or SIGNATURE query parameters not found.
    """

    DESCRIPTION = _('The URL has not been signed.')

    def __init__(self):
        super(NotSigned, self).__init__(self.DESCRIPTION)


class ResourceNotMatched(NotValid):
    """
    The URL and policy *resource* not matched.
    """

    DESCRIPTION = _('The URL and policy RESOURCE not matched.')

    def __init__(self):
        super(ResourceNotMatched, self).__init__(self.DESCRIPTION)


class ExtensionNotMatched(NotValid):
    """
    The URL and policy *resource* not matched.
    """

    DESCRIPTION = _('The {x} extension not matched.')

    def __init__(self, extension):
        super(ExtensionNotMatched, self).__init__(self.DESCRIPTION.format(x=extension))


class PolicyMalformed(NotValid):
    """
    The policy is malformed.
    """

    DESCRIPTION = _('The policy is malformed: {r}.')

    def __init__(self, reason):
        super(PolicyMalformed, self).__init__(self.DESCRIPTION.format(r=reason))


class PolicyNotAuthenticated(NotValid):
    """
    The policy signed with the private key and authenticated using
    the public key.
    """

    DESCRIPTION = _('Policy could not be validated using key and signature')

    def __init__(self):
        super(PolicyNotAuthenticated, self).__init__(self.DESCRIPTION)


class PolicyExpired(NotValid):
    """
    The signed policy has expired.
    """

    DESCRIPTION = _('Policy has expired')

    def __init__(self):
        super(PolicyExpired, self).__init__(self.DESCRIPTION)


class Base64(object):
    """
    Provides base64 encoding/decoding with exceptions
    mapped to DecodingError.
    """

    @staticmethod
    def encode(string):
        """
        Encode the specified object.

        :param string: A string to be encoded.
        :type string: str
        :return: The json string.
        :rtype: str
        """
        return urlsafe_b64encode(string)

    @staticmethod
    def decode(string):
        """
        Decode the specified base64 encoded string.

        :param string: A string to be decoded.
        :type string: str
        :return: The decoded string.
        :rtype: str
        :raise DecodingError: on error.
        """
        try:
            return urlsafe_b64decode(string)
        except TypeError, de:
            reason = str(de)
            raise DecodingError(reason)


class JSON(object):
    """
    Provides JSON encoding/decoding with exceptions
    mapped to DecodingError.
    """

    @staticmethod
    def encode(thing):
        """
        Encode the specified object.

        :param thing: A python object.
        :return: The json string.
        :rtype: str
        """
        return json.dumps(thing)

    @staticmethod
    def decode(string):
        """
        Decode the specified json encoded string.

        :param string: A json string.
        :type string: str
        :return: A python object.
        :raise DecodingError: on error.
        """
        try:
            return json.loads(string)
        except (TypeError, ValueError), de:
            reason = str(de)
            raise DecodingError(reason)


class Policy(object):
    """
    A signed URL policy.
    The *policy* is: {resource: <resource>, expiration: <seconds>, extensions: <ext>}
    The *resource* is the path?query in the original URL.
    The *expiration* is: seconds since epoch.

    :ivar resource: A resource that is the subject of the policy.
    :type resource: str
    :ivar expiration: The policy expiration (seconds since epoch).
    :type expiration: int
    :ivar extensions: Optional policy extensions.
    :type extensions: dict
    """

    RESOURCE = 'resource'
    EXPIRATION = 'expiration'
    EXTENSIONS = 'extensions'

    @staticmethod
    def digest(policy):
        """
        Get the hex digest for the specified policy.

        :param policy: A base64 encoded policy.
        :type policy: str
        :return: The hex digest.
        :rtype: str
        """
        _hash = sha256()
        _hash.update(policy)
        return _hash.hexdigest()

    @staticmethod
    def load(policy):
        """
        Load the policy.
        A policy object is created

        :param policy: A policy dictionary.
        :type policy: dict
        :return: The loaded policy object.
        :rtype: Policy
        :raise PolicyMalformed: on malformed policy.
        """
        # Empty
        if not policy:
            raise PolicyMalformed(_('EMPTY'))
        # Must be dictionary
        if not isinstance(policy, dict):
            raise PolicyMalformed(_('Must be <dict>'))
        # Resource Specified
        resource = policy.get(Policy.RESOURCE)
        if not resource:
            raise PolicyMalformed(_('Resource must be specified'))
        # Expiration Integer
        expiration = policy.get(Policy.EXPIRATION)
        if not isinstance(expiration, int):
            raise PolicyMalformed(_('Expiration must be integer'))
        # Extensions Dictionary
        extensions = policy.get(Policy.EXTENSIONS)
        if not isinstance(extensions, dict):
            raise PolicyMalformed(_('Extensions must be dictionary'))
        # Done
        policy = Policy(resource, int(expiration))
        policy.extensions = extensions
        return policy

    @staticmethod
    def decode(encoded):
        """
        Decode the base64 encoded json policy.

        :param encoded: A base64 encoded json policy.
        :type encoded: str
        :return: The decoded policy.
        :rtype: Policy
        """
        policy = Base64.decode(encoded)
        policy = JSON.decode(policy)
        policy = Policy.load(policy)
        return policy

    @staticmethod
    def validate(key, encoded, signature):
        """
        Decode and validate a policy.

        :param key: A public RSA key.
        :type key: RSA.RSA
        :param encoded: A base64 encoded json policy.
        :type encoded: str
        :param signature: A base64 encoded RSA signature.
        :type signature: str
        :return: The validated and decoded policy.
        :rtype: Policy
        :raise NotValid: if the signature and policy digest cannot be
            validated using the public key. Or, that the policy has expired.
        """
        try:
            digest = Policy.digest(encoded)
            if not key.verify(digest, Base64.decode(signature)):
                raise PolicyNotAuthenticated()
            policy = Policy.decode(encoded)
            if policy.expiration <= time():
                raise PolicyExpired()
            return policy
        except RSA.RSAError:
            raise PolicyNotAuthenticated()

    def __init__(self, resource, expiration):
        """
        :param resource: A resource that is the subject of the policy.
        :type resource: str
        :param expiration: The policy expiration (seconds since epoch).
        :type expiration: int
        """
        self.resource = resource
        self.expiration = expiration
        self.extensions = {}

    def encode(self):
        """
        Encode the policy.
        The policy is serialized to json.  Then, the json is base64 encoded.

        :return: The encoded policy.
        :rtype: str
        """
        policy = {
            Policy.RESOURCE: self.resource,
            Policy.EXPIRATION: self.expiration,
            Policy.EXTENSIONS: self.extensions
        }
        policy = JSON.encode(policy)
        policy = Base64.encode(policy)
        return policy

    def sign(self, key):
        """
        Sign the policy using the specified private RSA key.

        :param key: A private RSA key.
        :type key: RSA.RSA
        :return A tuple of: (encoded-policy, base64-signature)
        :rtype tuple
        """
        encoded = self.encode()
        digest = Policy.digest(encoded)
        signature = key.sign(digest)
        return encoded, Base64.encode(signature)

    def __str__(self):
        return str(self.__dict__)


class Query(object):
    """
    URL query.
    """

    @staticmethod
    def decode(encoded):
        """
        Decode the URL formatted parameters into a dictionary.

        :param encoded: A URL formatted parameters.
        :type encoded: str
        :return: The parameters as a dictionary.
        :rtype: dict
        """
        decoded = {}
        for pair in encoded.split(';'):
            if not pair:
                continue
            k, v = pair.split('=')
            decoded[k] = unquote(v)
        return decoded

    @staticmethod
    def encode(parsed):
        """
        Join the parsed parameters dictionary into URL parameter format.

        :param parsed: A parsed parameters.
        :type parsed: dict
        :return: A parameters string.  Eg: name=john;age=10
        :rtype: str
        """
        encoded = []
        for k, v in parsed.items():
            p = '{k}={v}'.format(k=k, v=quote(v))
            encoded.append(p)
        return ';'.join(encoded)


class Key(object):
    """
    Provides RSA key management.
    """

    @staticmethod
    def load(path=None, pem=None):
        """
        Get/Load an RSA key at the specified path.

        :param path: An absolute path to a PEM encoded key.
        :type path: str
        :param pem: A PEM encoded key.
        :type pem: str
        :return: The loaded key.
        :rtype: RSA.RSA
        """
        if path:
            with open(path) as fp:
                pem = fp.read()
        bfr = BIO.MemoryBuffer(pem)
        if 'PRIVATE' in pem:
            key = RSA.load_key_bio(bfr)
        else:
            key = RSA.load_pub_key_bio(bfr)
        return key


class URL(object):
    """
    An URL object that supports signing.

    :ivar content: The actual URL.
    :type content: ParseResult
    """

    POLICY = 'policy'
    SIGNATURE = 'signature'

    def __init__(self, content):
        """
        :param content: The *actual* URL key.
        :type content: str
        """
        self.content = urlparse(content)

    @property
    def scheme(self):
        """
        :return: The *scheme* component of the URL.
        :rtype: str
        """
        return self.content.scheme

    @property
    def netloc(self):
        """
        :return: The *host:port* component of the URL.
        :rtype: str
        """
        return self.content.netloc

    @property
    def path(self):
        """
        :return: The *path* component of the URL.
        :rtype: str
        """
        return self.content.path

    @property
    def params(self):
        """
        :return: The *params* component of the URL.
        :rtype: str
        """
        return self.content.params

    @property
    def query(self):
        """
        :return: The *query* component of the URL.
        :rtype: str
        """
        return self.content.query

    @property
    def resource(self):
        """
        :return: The *resource* specified by the URL.
        :rtype: str
        """
        path = self.path
        params = self.params
        query = self.query
        if params:
            params = ';{p}'.format(p=params)
        if query:
            query = '?{q}'.format(q=query)
        resource = [
            path,
            params,
            query
        ]
        return ''.join(resource)

    def sign(self, key, expiration=90, **extensions):
        """
        Sign the URL using the specified private RSA key.
        Has the format of: <url>?policy=<policy>;signature=<signature>.
        The *policy* is: {resource: <resource>, expiration: <seconds>, extensions: <ext>}
        The *resource* is the path?query in the original URL.
        The *expiration* is: seconds since epoch.
        The *signature* is RSA signature of the SHA256 digest of the
        json/base64 encoded policy.

        :param key: A private RSA key.
        :type key: RSA.RSA
        :param expiration: The signature expiration in seconds.
        :type expiration: int
        :param extensions: Optional policy extensions.
        :type extensions: dict
        :return: The signed URL.
        :rtype: SignedURL
        """
        expiration = int(time() + expiration)
        policy = Policy(self.resource, expiration)
        policy.extensions = extensions
        policy, signature = policy.sign(key)
        query = Query.decode(self.query)
        query[URL.SIGNATURE] = signature
        query[URL.POLICY] = policy
        signed = ParseResult(
            scheme=self.scheme,
            netloc=self.netloc,
            path=self.path,
            params=self.params,
            query=Query.encode(query),
            fragment='')
        return SignedURL(urlunparse(signed))

    def __str__(self):
        """
        :return: The URL *content*.
        :rtype: str
        """
        return urlunparse(self.content)


class SignedURL(URL):
    """
    A signed URL

    Has the format of: <url>?policy=<policy>;signature=<signature>.
    The *policy* is: {resource: <resource>, expiration: <expiration>}
    The *resource* is the path?query in the original URL.
    The *expiration* is: seconds since epoch.
    The *signature* is RSA signature of the SHA256 digest of the
    """

    @property
    def query(self):
        """
        :return: The *query* component of the URL with
            the policy and signature stripped.
        :rtype: str
        """
        query = Query.decode(self.content.query)
        query.pop(URL.POLICY, '')
        query.pop(URL.SIGNATURE, '')
        return Query.encode(query)

    @property
    def bundle(self):
        """
        :return: The (policy, signature) bundle.
        :rtype: tuple
        :raise NotSigned: when either the policy
            or signature is not found.
        """
        try:
            query = Query.decode(self.content.query)
            return query[URL.POLICY], query[URL.SIGNATURE]
        except KeyError:
            raise NotSigned()

    def validate(self, key, **extensions):
        """
        Validate the URL *content* using the RSA signature and the
        public key specified by *key*.  The policy is validated.
        Then, the resource in the policy is matched against the resource
        specified in the URL.  Last, the policy extensions are matched
        against the specified extensions.

        :param key: A public RSA key.
        :type key: RSA.RSA
        :param extensions: Optional policy extensions.
        :type extensions: dict
        :return: The resource specified in the policy.
        :rtype: str
        :raise NotValid: if the signature and policy digest cannot be
            validated using the public key. Or, that the policy has expired.
        """
        policy, signature = self.bundle
        policy = Policy.validate(key, policy, signature)
        if self.resource != policy.resource:
            raise ResourceNotMatched()
        for k, v in policy.extensions.items():
            if extensions.get(k) != v:
                raise ExtensionNotMatched(k)
        return policy.resource
