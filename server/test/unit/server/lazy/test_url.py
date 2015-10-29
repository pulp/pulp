from collections import OrderedDict
from unittest import TestCase

from mock import patch, Mock, PropertyMock
from M2Crypto import RSA

from pulp.server.lazy.url import (
    NotValid, DecodingError, NotSigned, ResourceNotMatched, ExtensionNotMatched, PolicyMalformed,
    PolicyNotAuthenticated, PolicyExpired, Base64, JSON, Policy, Query, Key, URL, SignedURL)


MODULE = 'pulp.server.lazy.url'


class TestExceptions(TestCase):

    def test_not_valid(self):
        self.assertTrue(isinstance(NotValid(), Exception))

    def test_decoding_error(self):
        reason = '1234'
        e = DecodingError(reason)
        self.assertTrue(isinstance(e, Exception))
        self.assertEqual(e.args[0], e.DESCRIPTION.format(r=reason))

    def test_not_signed(self):
        e = NotSigned()
        self.assertTrue(isinstance(e, Exception))
        self.assertEqual(e.args[0], e.DESCRIPTION)

    def test_resource_not_matched(self):
        e = ResourceNotMatched()
        self.assertTrue(isinstance(e, Exception))
        self.assertEqual(e.args[0], e.DESCRIPTION)

    def test_extension_not_matched(self):
        extension = '1234'
        e = ExtensionNotMatched(extension)
        self.assertTrue(isinstance(e, Exception))
        self.assertEqual(e.args[0], e.DESCRIPTION.format(x=extension))

    def test_policy_malformed(self):
        reason = '1234'
        e = PolicyMalformed(reason)
        self.assertTrue(isinstance(e, Exception))
        self.assertEqual(e.args[0], e.DESCRIPTION.format(r=reason))

    def test_policy_not_authenticated(self):
        e = PolicyNotAuthenticated()
        self.assertTrue(isinstance(e, Exception))
        self.assertEqual(e.args[0], e.DESCRIPTION)

    def test_policy_expired(self):
        e = PolicyExpired()
        self.assertTrue(isinstance(e, Exception))
        self.assertEqual(e.args[0], e.DESCRIPTION)


class TestBase64(TestCase):

    @patch(MODULE + '.urlsafe_b64encode')
    def test_encode(self, encode):
        s = '1234'
        encoded = Base64.encode(s)
        encode.assert_called_once_with(s)
        self.assertEqual(encoded, encode.return_value)

    @patch(MODULE + '.urlsafe_b64decode')
    def test_decode(self, decode):
        s = '1234'
        decoded = Base64.decode(s)
        decode.assert_called_once_with(s)
        self.assertEqual(decoded, decode.return_value)

    @patch(MODULE + '.urlsafe_b64decode')
    def test_decode_error(self, decode):
        decode.side_effect = TypeError()
        self.assertRaises(DecodingError, Base64.decode, '')


class TestJson(TestCase):

    @patch(MODULE + '.json')
    def test_encode(self, json):
        s = '1234'
        encoded = JSON.encode(s)
        json.dumps.assert_called_once_with(s)
        self.assertEqual(encoded, json.dumps.return_value)

    @patch(MODULE + '.json')
    def test_decode(self, json):
        s = '1234'
        decoded = JSON.decode(s)
        json.loads.assert_called_once_with(s)
        self.assertEqual(decoded, json.loads.return_value)

    @patch(MODULE + '.json')
    def test_decode_value_error(self, json):
        json.loads.side_effect = ValueError()
        self.assertRaises(DecodingError, JSON.decode, '')

    @patch(MODULE + '.json')
    def test_decode_type_error(self, json):
        json.loads.side_effect = TypeError()
        self.assertRaises(DecodingError, JSON.decode, '')


class TestPolicy(TestCase):

    def test_init(self):
        resource = 'r123'
        expiration = 10
        policy = Policy(resource, expiration)
        self.assertEqual(policy.resource, resource)
        self.assertEqual(policy.expiration, expiration)
        self.assertEqual(policy.extensions, {})

    @patch(MODULE + '.sha256')
    def test_digest(self, sha256):
        p = '1234'
        digest = Policy.digest(p)
        sha256.assert_called_once_with()
        sha256.return_value.update.assert_called_once_with(p)
        self.assertEqual(digest, sha256.return_value.hexdigest.return_value)

    def test_load_empty(self):
        self.assertRaises(PolicyMalformed, Policy.load, {})

    def test_load_non_dict(self):
        self.assertRaises(PolicyMalformed, Policy.load, 10)

    def test_load_no_resource(self):
        policy = {
            Policy.EXPIRATION: 100
        }
        self.assertRaises(PolicyMalformed, Policy.load, policy)

    def test_load_invalid_expiration(self):
        policy = {
            Policy.RESOURCE: 'dog',
            Policy.EXPIRATION: '1234'
        }
        self.assertRaises(PolicyMalformed, Policy.load, policy)

    def test_load_invalid_extensions(self):
        policy = {
            Policy.RESOURCE: 'dog',
            Policy.EXPIRATION: 10,
            Policy.EXTENSIONS: None
        }
        self.assertRaises(PolicyMalformed, Policy.load, policy)

    def test_load(self):
        policy = {
            Policy.RESOURCE: 'dog',
            Policy.EXPIRATION: 10,
            Policy.EXTENSIONS: {'remote_ip': '63.10.133'}
        }
        loaded = Policy.load(policy)
        self.assertTrue(isinstance(loaded, Policy))
        self.assertEqual(loaded.resource, policy[Policy.RESOURCE])
        self.assertEqual(loaded.expiration, policy[Policy.EXPIRATION])
        self.assertEqual(loaded.extensions, policy[Policy.EXTENSIONS])

    @patch(MODULE + '.Policy.load')
    @patch(MODULE + '.JSON')
    @patch(MODULE + '.Base64')
    def test_decode(self, base62, json, load):
        encoded = '1234'
        decoded = Policy.decode(encoded)
        base62.decode.assert_called_once_with(encoded)
        json.decode.assert_called_once_with(base62.decode.return_value)
        load.assert_called_once_with(json.decode.return_value)
        self.assertEqual(decoded, load.return_value)

    @patch(MODULE + '.time')
    @patch(MODULE + '.Base64')
    @patch(MODULE + '.Policy.decode')
    @patch(MODULE + '.Policy.digest')
    def test_validate(self, digest, decode, base64, time):
        time.return_value = 10
        decode.return_value = Policy('', 20)
        key = Mock()
        encoded = '12345=='
        signature = '0x44'

        # test
        policy = Policy.validate(key, encoded, signature)

        # validation
        digest.assert_called_once_with(encoded)
        base64.decode.assert_called_once_with(signature)
        key.verify.assert_called_once_with(digest.return_value, base64.decode.return_value)
        decode.assert_called_once_with(encoded)
        self.assertEqual(policy, decode.return_value)

    @patch(MODULE + '.Base64', Mock())
    @patch(MODULE + '.Policy.digest', Mock())
    def test_validate_invalid_signature(self):
        key = Mock()
        key.verify.return_value = False
        self.assertRaises(PolicyNotAuthenticated, Policy.validate, key, '', '')

    @patch(MODULE + '.Base64', Mock())
    @patch(MODULE + '.Policy.digest', Mock())
    def test_validate_rsa_error(self):
        key = Mock()
        key.verify.side_effect = RSA.RSAError
        self.assertRaises(PolicyNotAuthenticated, Policy.validate, key, '', '')

    @patch(MODULE + '.time')
    @patch(MODULE + '.Policy.decode')
    @patch(MODULE + '.Base64', Mock())
    @patch(MODULE + '.Policy.digest', Mock())
    def test_validate_policy_expired(self, decode, time):
        time.return_value = 20
        decode.return_value = Policy('', 10)
        key = Mock()
        self.assertRaises(PolicyExpired, Policy.validate, key, '', '')

    @patch(MODULE + '.JSON')
    @patch(MODULE + '.Base64')
    def test_encode(self, base64, json):
        resource = 'r123'
        expiration = 10
        policy = Policy(resource, expiration)
        policy.extensions = {'remote_ip': '10.1.1.1'}
        encoded = policy.encode()
        json.encode.assert_called_once_with(
            {
                Policy.RESOURCE: policy.resource,
                Policy.EXPIRATION: policy.expiration,
                Policy.EXTENSIONS: policy.extensions
            })
        base64.encode.assert_called_once_with(json.encode.return_value)
        self.assertEqual(encoded, base64.encode.return_value)

    @patch(MODULE + '.Base64')
    @patch(MODULE + '.Policy.digest')
    @patch(MODULE + '.Policy.encode')
    def test_sign(self, encode, digest, base64):
        resource = 'r123'
        expiration = 10
        policy = Policy(resource, expiration)
        policy.extensions = {'remote_ip': '10.1.1.1'}
        key = Mock()

        # test
        signed = policy.sign(key)

        # validation
        digest.assert_called_once_with(encode.return_value)
        key.sign.assert_called_once_with(digest.return_value)
        base64.encode.assert_called_once_with(key.sign.return_value)
        self.assertEqual(signed, (encode.return_value, base64.encode.return_value))

    def test_str(self):
        policy = Policy('r123', 10)
        self.assertEqual(str(policy), str(policy.__dict__))


class TestQuery(TestCase):

    def test_decode(self):
        encoded = ';name=john;age=12;'
        decoded = Query.decode(encoded)
        self.assertEqual(decoded, {'name': 'john', 'age': '12'})

    def test_encode(self):
        decoded = OrderedDict()
        decoded['name'] = 'john'
        decoded['age'] = '12'
        encoded = Query.encode(decoded)
        self.assertEqual(encoded, 'name=john;age=12')


class TestKey(TestCase):

    @patch(MODULE + '.RSA')
    @patch(MODULE + '.BIO')
    @patch('__builtin__.open')
    def test_load_pub(self, _open, bio, rsa):
        path = '/tmp/key.pem'
        pem = '-----BEGIN PUBLIC KEY-----'
        fp = Mock()
        fp.__enter__ = Mock(return_value=fp)
        fp.__exit__ = Mock()
        fp.read.return_value = pem
        _open.return_value = fp

        # test
        key = Key.load(path=path)

        # validation
        _open.assert_called_once_with(path)
        fp.__enter__.assert_called_once_with()
        fp.__exit__.assert_called_once_with(None, None, None)
        bio.MemoryBuffer.assert_called_once_with(pem)
        rsa.load_pub_key_bio.assert_called_once_with(bio.MemoryBuffer.return_value)
        self.assertEqual(key, rsa.load_pub_key_bio.return_value)

    @patch(MODULE + '.RSA')
    @patch(MODULE + '.BIO')
    @patch('__builtin__.open')
    def test_load_private(self, _open, bio, rsa):
        path = '/tmp/key.pem'
        pem = '-----BEGIN RSA PRIVATE KEY-----'
        fp = Mock()
        fp.__enter__ = Mock(return_value=fp)
        fp.__exit__ = Mock()
        fp.read.return_value = pem
        _open.return_value = fp

        # test
        key = Key.load(path=path)

        # validation
        _open.assert_called_once_with(path)
        fp.__enter__.assert_called_once_with()
        fp.__exit__.assert_called_once_with(None, None, None)
        bio.MemoryBuffer.assert_called_once_with(pem)
        rsa.load_key_bio.assert_called_once_with(bio.MemoryBuffer.return_value)
        self.assertEqual(key, rsa.load_key_bio.return_value)


class TestURL(TestCase):

    @patch(MODULE + '.urlparse')
    def test_init(self, urlparse):
        s = 'http://host:port?age=10'
        url = URL(s)
        urlparse.assert_called_once_with(s)
        self.assertEqual(url.content, urlparse.return_value)

    def test_properties(self):
        url = URL('http://redhat.com:1234/path;p1;p2?age=10')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.netloc, 'redhat.com:1234')
        self.assertEqual(url.path, '/path')
        self.assertEqual(url.params, 'p1;p2')
        self.assertEqual(url.query, 'age=10')
        self.assertEqual(url.resource, '/path;p1;p2?age=10')

    @patch(MODULE + '.Policy')
    @patch(MODULE + '.time')
    def test_sign(self, time, policy):
        time.return_value = 10
        url = URL('http://redhat.com:1234/path;p1;p2?age=10')
        key = Mock()
        expiration = 10
        signature = 's1234['
        encoded_policy = 'p1234['
        _policy = Mock()
        _policy.sign.return_value = (encoded_policy, signature)
        policy.return_value = _policy
        extensions = dict(remote_ip='10.1.1.1')

        # test
        signed = url.sign(key, expiration, **extensions)

        # validation
        query = dict(Query.decode(url.query))
        query[URL.POLICY] = encoded_policy
        query[URL.SIGNATURE] = signature
        policy.assert_called_once_with(url.resource, expiration + time.return_value)
        self.assertEqual(signed.scheme, url.scheme)
        self.assertEqual(signed.netloc, url.netloc)
        self.assertEqual(signed.params, url.params)
        self.assertEqual(signed.path, url.path)
        self.assertEqual(signed.query, url.query)
        self.assertEqual(signed.bundle, (encoded_policy, signature))

    def test_str(self):
        url = 'https://redhat.com:443/path;p1;p2?q1=1;q2=2'
        self.assertEqual(str(URL(url)), url)


class TestSignedURL(TestCase):

    def test_query(self):
        bundle = Query.encode(
            {
                URL.POLICY: 'p1234[',
                URL.SIGNATURE: 's1234['
            })
        query = 'age=10'
        url = SignedURL('https://pulp.org/content?{b};{q}'.format(b=bundle, q=query))
        self.assertEqual(url.query, query)

    def test_query_no_signature(self):
        query = 'age=10'
        url = SignedURL('https://pulp.org/content?{q}'.format(q=query))
        self.assertEqual(url.query, query)

    def test_bundle(self):
        policy = 'p1234['
        signature = 's1234['
        bundle = Query.encode(
            {
                URL.POLICY: policy,
                URL.SIGNATURE: signature
            })
        query = 'age=10'
        url = SignedURL('https://pulp.org/content?{b};{q}'.format(b=bundle, q=query))
        self.assertEqual(url.bundle, (policy, signature))

    def test_bundle_when_not_signed(self):
        url = SignedURL('https://pulp.org/content')
        self.assertRaises(NotSigned, getattr, url, 'bundle')

    @patch(MODULE + '.Policy')
    @patch(MODULE + '.SignedURL.bundle', new_callable=PropertyMock)
    def test_validate(self, bundle, policy):
        remote_ip = '10.1.23.11'
        resource = '/content/good/stuff'
        _policy = Mock(
            resource=resource,
            expiration=0,
            extensions=dict(remote_ip=remote_ip)
        )
        bundle.return_value = ('p1234[', 's1234[')
        policy.validate.return_value = _policy
        key = Mock()

        # test
        url = SignedURL('https://pulp.org{r}'.format(r=resource))
        _resource = url.validate(key, remote_ip=remote_ip)

        # validation
        policy.validate.assert_called_once_with(
            key, bundle.return_value[0], bundle.return_value[1])
        self.assertEqual(_resource, resource)

    @patch(MODULE + '.Policy')
    @patch(MODULE + '.SignedURL.bundle', new_callable=PropertyMock)
    def test_validate_resource_not_matched(self, bundle, policy):
        resource = '/content/good/stuff'
        _policy = Mock(
            resource='bogus',
            expiration=0,
            extensions={}
        )
        bundle.return_value = ('p1234[', 's1234[')
        policy.validate.return_value = _policy
        key = Mock()

        # test
        url = SignedURL('https://pulp.org{r}'.format(r=resource))
        self.assertRaises(ResourceNotMatched, url.validate, key)

    @patch(MODULE + '.Policy')
    @patch(MODULE + '.SignedURL.bundle', new_callable=PropertyMock)
    def test_validate_extension_not_matched(self, bundle, policy):
        remote_ip = '10.1.23.11'
        resource = '/content/good/stuff'
        _policy = Mock(
            resource=resource,
            expiration=0,
            extensions=dict(remote_ip='66.1.123.10')
        )
        bundle.return_value = ('p1234[', 's1234[')
        policy.validate.return_value = _policy
        key = Mock()

        # test
        url = SignedURL('https://pulp.org{r}'.format(r=resource))
        self.assertRaises(ExtensionNotMatched, url.validate, key, remote_ip=remote_ip)
