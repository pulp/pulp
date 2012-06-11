#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
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

import logging
import unittest

from pulp.server.auth.certificate import Certificate
from pulp.server.auth.cert_generator import SerialNumber
import pulp.server.auth.cert_generator as cert_generator

SerialNumber.PATH = '/tmp/sn.dat'
sn = SerialNumber()
sn.reset()


# The following certificate was signed by the pulp CA
# (<code root>/etc/pki/pulp/ca.crt)
VALID_CERT = '''
-----BEGIN CERTIFICATE-----
MIID2jCCAsICAQEwDQYJKoZIhvcNAQEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0
MB4XDTEwMDgyNTEyNTkzNVoXDTExMDgyNTEyNTkzNVowUjELMAkGA1UEBhMCVVMx
CzAJBgNVBAgMAk5DMRAwDgYDVQQHDAdSYWxlaWdoMRAwDgYDVQQKDAdSZWQgSGF0
MRIwEAYDVQQDDAlsb2NhbGhvc3QwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIK
AoICAQChxWk1A/0zpGOctuo7XDbTsguEYEnmbw2dcr9EmZ0ntUYr0Jr5nsbpIL0l
fyTrgKySqr8ebDc6srnkbjl4kXi7nBC58CTonqVHlqtxGFHScnoK2OAsR4K+xGEP
3zJ/ciJ4XRH9++p5PH3oNIFMru8+NONyL8BuoydI8t4afpTIIFwGP2mGRn4o8LAS
Mq8yQCAa8toriZ/0BK3lA0Sa+A4a5EF67v6vGnVcCDKSWIeB3SpSMCmv5CiYZjrN
PRMjfK+d9lHVGLv9AW8TAbfALfjLnw4oBT0yOkgr4LzdJLAO/6iNqE39aivQzZDO
loCZBVDllztgkUYqlzwzu7fMdcMktXi9wMp4eLiMmIA89AqQA6EeEMHM8xNx64Ij
nYfIctoQDJBbHOeuhAbTkWhkDDAEvmLRlqVZz20qNvkWytHY3GYOU8JdHVUGgXic
V0FRFXZ2FO9UN51lQdUVpPjh6Txoqwht2ep3NlU2LhYol2YSlOk4K5tXGZGXf/qL
jQZnAEmMV37v3yYXlh3ig1u3/nTz77SJQf1KEPGmAA+f2P5kkTaD+BGdizB2m0ho
+gRPQTouNNMnSQdnqD39VPBUNpHrZgA17HOB5oZGF/6x8FAzbF4k2ExES5zrp5KY
7LxSbwQgJrQxkts4yMQFPpNXKd6u1xLxKz4MGVfspZbRaB407wIDAQABMA0GCSqG
SIb3DQEBBQUAA4IBAQBRx1bHvaZqcakHIP70M3hquCdaP3zO5AMX3ZFhcEIUIIbq
92TcOvCq0ZUDyjh+hxiCxwPSbbRO7QEiCup0UGRBmQPesk76E+nw1z7jxYom/42h
dIjK01IpgdRf25im4NttngtoMEO6qWQfc6cKmBL7Sqxsg9oiHSVcRk7CahGqWMwT
12q+CZB9GHbGwqDGXgd3LgQ0Mi1vXW3tAhX58msTV13FPH+pEs2suWLAeRc8O9RI
kFRZNej7n3qrj/ObW9a9pa+uo9Su6+EryFJjG7+rp2YXbA+4jT4u+DCV8C62fvZH
sCE6nMbER6n0eQzlND2hUHB97ZK5PUT+t42SMOaf
-----END CERTIFICATE-----
'''

# The following cert was signed by a non-pulp CA
INVALID_CERT = '''
-----BEGIN CERTIFICATE-----
MIIFRDCCAywCAQEwDQYJKoZIhvcNAQEFBQAwfjELMAkGA1UEBhMCVVMxCzAJBgNV
BAgMAk5KMRIwEAYDVQQHDAlNaWNrbGV0b24xDTALBgNVBAoMBGpkb2IxDTALBgNV
BAsMBGpkb2IxDTALBgNVBAMMBGpkb2IxITAfBgkqhkiG9w0BCQEWEmpkb2JpZXNA
cmVkaGF0LmNvbTAeFw0xMDA4MjUxMzAwMTdaFw0xMTA4MjUxMzAwMTdaMFIxCzAJ
BgNVBAYTAlVTMQswCQYDVQQIDAJOQzEQMA4GA1UEBwwHUmFsZWlnaDEQMA4GA1UE
CgwHUmVkIEhhdDESMBAGA1UEAwwJbG9jYWxob3N0MIICIjANBgkqhkiG9w0BAQEF
AAOCAg8AMIICCgKCAgEAocVpNQP9M6RjnLbqO1w207ILhGBJ5m8NnXK/RJmdJ7VG
K9Ca+Z7G6SC9JX8k64Cskqq/Hmw3OrK55G45eJF4u5wQufAk6J6lR5arcRhR0nJ6
CtjgLEeCvsRhD98yf3IieF0R/fvqeTx96DSBTK7vPjTjci/AbqMnSPLeGn6UyCBc
Bj9phkZ+KPCwEjKvMkAgGvLaK4mf9ASt5QNEmvgOGuRBeu7+rxp1XAgykliHgd0q
UjApr+QomGY6zT0TI3yvnfZR1Ri7/QFvEwG3wC34y58OKAU9MjpIK+C83SSwDv+o
jahN/Wor0M2QzpaAmQVQ5Zc7YJFGKpc8M7u3zHXDJLV4vcDKeHi4jJiAPPQKkAOh
HhDBzPMTceuCI52HyHLaEAyQWxznroQG05FoZAwwBL5i0ZalWc9tKjb5FsrR2Nxm
DlPCXR1VBoF4nFdBURV2dhTvVDedZUHVFaT44ek8aKsIbdnqdzZVNi4WKJdmEpTp
OCubVxmRl3/6i40GZwBJjFd+798mF5Yd4oNbt/508++0iUH9ShDxpgAPn9j+ZJE2
g/gRnYswdptIaPoET0E6LjTTJ0kHZ6g9/VTwVDaR62YANexzgeaGRhf+sfBQM2xe
JNhMREuc66eSmOy8Um8EICa0MZLbOMjEBT6TVynertcS8Ss+DBlX7KWW0WgeNO8C
AwEAATANBgkqhkiG9w0BAQUFAAOCAgEADObqR11wiOTa5mv7lAkB/VfQOqEvlUdd
8oKoPQ/qsscA1vt1zrtqX+6WabdfyiWF6daM8EENsw+KE0If9LL36IZ0SeewvGJ/
DZe+3vQvgXSKuXD4qHILvFi31A7s+xngK6uxtsSrQ7HQh6dzvXdN/zhcXqeNKGDr
7EHASGn+9PvqZOOVZPYSap9X9xTHrX/xOpuQDdvcgFy0EZ9ypxG4XC7sgBL26Rag
39flGwkF9cYsbbsfkxVPuXdyQ4CwJ+5yXDX+1VVFVQAn+OcX3aup87Db1Z+1jk/Y
9lITvN31LaAnY7obBaLABGSDQ5x4y/3u/4eNPE9h5MoO51/1uECJ+ycYggizDqCc
nJkKFXd7Je6BzPLvdok2jz4cm49gf7nBfYUt0wsmCsgvIYWr7IdF1eWM573NjuUn
SPQYN7bDo28Ad5hpSt4XVewyz2HjXX2oiyjWAMKtpr2xQ1g1PQG8FxddoVpGlQDH
V8W9qjnfc00jydWmjrrWn6IbJG7CVkN8QW9L0QkaBv+iHmF8eMvlfZ59xsX2zLr8
MY4jR9gzz9eDjOf6OwdylwrrHrBCkGYuG10GAEjiWB9/PwM2r5qmM7D4IZy8errZ
Y45cgKkgKk4VnpBC7n1xtKZIH/nbsuUEiRJrgURNitJdjjkBsbeu0oxtsqe3ty1Z
XGuaPqfHaos=
-----END CERTIFICATE-----
'''


class TestCertGeneration(unittest.TestCase):

    def test_priv_key(self):
        # Test
        pem = cert_generator._make_priv_key()

        # Verify
        self.assertTrue(pem.startswith('-----BEGIN RSA PRIVATE KEY-----'))

    def test_generation(self):
        # Setup
        cid = "foobarbaz"

        # Test
        pk, x509_pem = cert_generator.make_cert(cid, 7)

        # Verify
        self.assertTrue(pk is not None)
        self.assertTrue(x509_pem is not None)

        cert = Certificate(content=x509_pem)
        subject = cert.subject()
        consumer_cert_uid = subject.get('CN', None)
        self.assertEqual(cid, consumer_cert_uid)

    def test_verify(self):
        # Test
        valid_result = cert_generator.verify_cert(VALID_CERT)
        self.assertTrue(valid_result)

        invalid_result = cert_generator.verify_cert(INVALID_CERT)
        self.assertTrue(not invalid_result)

if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.INFO)
    unittest.main()
