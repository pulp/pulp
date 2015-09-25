from unittest import TestCase

from mock import patch

from pulp.server.lazy.url import (
    DecodingError,
    Key,
    NotSigned,
    NotValid,
    PolicyExpired,
    PolicyNotAuthenticated,
    SignedURL,
    URL,)


MODULE = 'pulp.server.lazy.url'

KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEAoVb2r9uT4kd8E75o7Cjav+PWmH+I8z/iU0d6Ilj+n1A2TvjK
OG0b3ZWnglQcWPcgrWs1JmraibKtekCj3Fq/QiFMTZXUDKdjOVse08Tr8D9BVa6a
j7xAawwm09PC3TTuXZTxzt4URT56I2bKr+M0qK4Ojto2iJE1aJdyMON3E8EWXidr
PtDDNu6v6tv5krgh/4ZZ35+KXY+M5x8ByTGV1G0g+NtQsyDtYefspiIIapZeWcpj
sZuWkxcjqZwiPDN5n41za6WM202FMFMGjOWLKuuLMZmAtrF3d6NZ685Pfqw7B4zS
zPJopg24Nd2o0ih5/eG/qULkJQ+UDJchxEnjNQIDAQABAoIBAQCOQhm9sgTRTmqv
FgN5yAQpkoGTcVCV+0xaVfnw8zt/ycA5HdFgs4QQe3Z5yiQ8pZqgjpkMyMbtBylD
VF+nWjSt4KJg/q08gxNQbXHfFBFdgsje/de2ySybttk9iciWN6e9yCj2WIbTD2Wu
dWJeeB3kZaTcfLf87tyC3paHWOmT9hRW6dm9wNJDR5Yg/xKplEqiotARVT3T4Lov
qOYrLDpXqjT9ObTF30s6LDyw4R9Jp8zYR6q44q3A4hntiysL/YyP+PouWw1Gfppd
/V7gL/aR2uvMXQAij74irsGR9tKlh7Izxv8L1dnPD0cVDY9Hsw0EOfOqI50/1sSy
t3hvIzK5AoGBANMAmaaRM/t8eNbWyVh7iPtBGX7yai8O5Xb9uoAK8QuNvCjC3K53
AIEvOsXhLO/Q7KgzEndx9Kb4Kaov+t2x9o/Kq/HBfkOF35jLzsL2BsfS9xWCJhdp
QUpZCc8/Q8YH9IrLW8BASijxDtsnwKG+Rv1aYvpwa9J6KO+WqAieyjtzAoGBAMO/
GIIqc4SO4tvLwjuMhEDcHlLL8O619H5xiy7EL84jMdAV0eXwKIimkjiitphPED2N
vBCk6zpn1MAwyOWq+VnxWdrfddWe2J+411EBeSryljSi6PVb3P6+Mi00J6LGp0fG
WD13Bnq/dGmEAWHRrOObbZT6OAedFC6PKtRBUAy3AoGBAIm4opFtxRgorlbL6q+u
MkKMwy9w2o3Mk0mPYuOgQKTh5iZUyeW2FsY7JYly5/m/zDgc3bjI0H8LC2bh2kRJ
nD1Oc9xgByHbh44buODX5KUYtd18DZDKSqtUYmq7SGlBWAQfp8tcKwt+C8xPrhPk
NkG3dVMxfa7rvTxkgVjfC/CxAoGBAIczbGgrjhJW5tZNjGC5E3gBEWi6uDUItFDJ
eArbMvG8WWGSUKHzGOwZsRExQdE9esgpJ2aPonF62fXNPFV1nDjFfPyyL59W0eSw
NPgcfmZtm9XLWABwbNn+4IVcaqwBbfUjSDtcBLuvlWZz6Mh5nGKxLiUiFqUbl574
/+oPGo1NAoGAA9n13njeTQ866Czf/pwyr7hTEnYif4R233VT1O9yXu9JwkUqg8/k
oUzuL5QxyyGmOVT9TDbujMOwfMZCq/9ldR8+ySFZfj7PZOJ4/t7+HT17gX1hDMA3
KUjssHsK51UOzBJVSxE+39rbyFd6GhILOxBh9XR2D68tfTBHq4oKW3U=
-----END RSA PRIVATE KEY-----
"""

PUB = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAoVb2r9uT4kd8E75o7Cja
v+PWmH+I8z/iU0d6Ilj+n1A2TvjKOG0b3ZWnglQcWPcgrWs1JmraibKtekCj3Fq/
QiFMTZXUDKdjOVse08Tr8D9BVa6aj7xAawwm09PC3TTuXZTxzt4URT56I2bKr+M0
qK4Ojto2iJE1aJdyMON3E8EWXidrPtDDNu6v6tv5krgh/4ZZ35+KXY+M5x8ByTGV
1G0g+NtQsyDtYefspiIIapZeWcpjsZuWkxcjqZwiPDN5n41za6WM202FMFMGjOWL
KuuLMZmAtrF3d6NZ685Pfqw7B4zSzPJopg24Nd2o0ih5/eG/qULkJQ+UDJchxEnj
NQIDAQAB
-----END PUBLIC KEY-----
"""


KEY = Key.load(pem=KEY)
PUB = Key.load(pem=PUB)


class TestSigning(TestCase):

    def test_basic_signing(self):
        url = URL('http://redhat.com/content/jit.rpm')
        url = url.sign(KEY)
        print url

    def test_signing_and_validation(self):
        uri = '/content/jit.rpm'
        url = URL('http://redhat.com{r}'.format(r=uri))
        url = url.sign(KEY)
        resource = url.validate(PUB)
        self.assertEqual(resource, uri)

    def test_signing_and_validation_with_query(self):
        uri = '/content/jit.rpm?hello=world'
        url = URL('http://redhat.com{r}'.format(r=uri))
        url = url.sign(KEY)
        resource = url.validate(PUB)
        self.assertEqual(resource, uri)

    def test_signing_and_validation_with_params(self):
        uri = '/content/jit.rpm;hello=world'
        url = URL('http://redhat.com{r}'.format(r=uri))
        url = url.sign(KEY)
        resource = url.validate(PUB)
        self.assertEqual(resource, uri)

    @patch(MODULE + '.time')
    def test_policy_expired(self, time):
        time.side_effect = [1, 2]
        url = URL('http://redhat.com/content/jit.rpm')
        url = url.sign(KEY, 1)
        self.assertRaises(PolicyExpired, url.validate, PUB)

    def test_validate_resources_not_matched(self):
        url = URL('http://redhat.com/content/jit.rpm')
        url = url.sign(KEY)
        content = str(url)
        url = SignedURL(content.replace('content', 'free/content'))
        self.assertRaises(NotValid, url.validate, PUB)

    def test_policy_altered(self):
        url = URL('http://redhat.com/content/jit.rpm')
        url = url.sign(KEY)
        content = str(url)
        url = SignedURL(content.replace('policy=', 'policy=1'))
        self.assertRaises(PolicyNotAuthenticated, url.validate, PUB)

    def test_signature_decoding(self):
        url = URL('http://redhat.com/content/jit.rpm')
        url = url.sign(KEY)
        content = str(url)
        url = SignedURL(content.replace('signature=', 'signature=XXX'))
        self.assertRaises(DecodingError, url.validate, PUB)

    def test_no_policy(self):
        url = URL('http://redhat.com/content/jit.rpm')
        url = url.sign(KEY)
        content = str(url)
        url = SignedURL(content.replace('policy=', 'age='))
        self.assertRaises(NotSigned, url.validate, PUB)

    def test_no_signature(self):
        url = URL('http://redhat.com/content/jit.rpm')
        url = url.sign(KEY)
        content = str(url)
        url = SignedURL(content.replace('signature=', 'age='))
        self.assertRaises(NotSigned, url.validate, PUB)
