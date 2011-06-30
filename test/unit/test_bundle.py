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

import os
import sys
import shutil
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.common.bundle import Bundle

KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAxGSOx4CjDp4f8iBZvnMPjtBEDQ2j2M2oYvqidFJhoyMJMpy7
dPWc9sFNWXFJDD1xqHZqdegloVnMhxztzRE8YyklHfBV7/Sw4ExN4PQIUfB2GKfa
WjvkAwuV1z/up6e4xP1vFpApncwNFtqXP4RIhcVk/H87LZynm9bCrc4RABxHAyF1
hl9GOgpn7FD6QeF0kPgFpqR57y/I/ajdP7EtjZk4EEu26HKkH3pCsIRKjMvy7ZhL
cOpurVfSB7R65v+WT5AwOOu0XmRMLjmOAkTKR1EWGArOc7kgDCce3k29nXBDEX+U
C+3qUEbm31e4VXVxA4uITsHOSUOM5f3s7L0nEwIDAQABAoIBAQCxBnt09U0FZh8h
n2uFsi15690Lbxob2PVJkuZQt9lutawaxRBsEuETw5Y3Y1gXAmOrGGJKOaGB2XH0
8GyiBkFKmNHuNK8iBoxRAjbI6O9+/KNXAiZeY9HZtN2yEtzKnvJ8Dn3N9tCsfjvm
N89R36mHezDWMNFlAepLHMCK7k6Aq2XfMSgHJMmHYv2bBdcnbPidl3kr8Iq3FLL2
0qoiou+ihvKEj4SAguQNuR8w5oXKc5I3EdmXGGJ0WlZM2Oqg7qL85KhQTg3WEeUj
XB4cLC4WoV0ukvUBuaCFCLdqOLmHk2NB3b4DEYlEIsz6XiE3Nt7cBO2HBPa/nTFl
qAvXxQchAoGBAPpY1S1SMHEWH2U/WH57jF+Yh0yKPPxJ6UouG+zzwvtm0pfg7Lkn
CMDxcTTyMpF+HjU5cbJJrVO/S1UBnWfxFdbsWFcw2JURqXj4FO4J5OcVHrQEA6KY
9HBdPV6roTYVIUeKZb6TxIC85b/Xkcb3AHYtlDg3ygOjFKD6NUVNHIebAoGBAMjT
1bylHJXeqDEG+N9sa1suH7nMVsB2PdhsArP3zZAoOIP3lLAdlQefTyhpeDgYbFqD
wxjeFHDuJjxIvB17rPCKa8Rh4a0GBlhKEDLm+EM3H0FyZ0Yc53dckgDOnJmyh9f+
8fc7nYqXEA7sD0keE9ANGS+SLV9h9v9A7og7bGHpAoGAU/VU0RU+T77GmrMK36hZ
pHnH7mByIX48MfeSv/3kR2HtgKgbW+D+a47Nk58iXG76fIkeW1egPHTsM78N5h0R
YPn0ipFEIYJB3uL8SfShguovWNn7yh0X5VMv0L8omrWtaou8oZR3E2HGf3cxWZPe
4MNacRwssNmRgodHNE2vIr8CgYABp50vPL0LjxYbsU8DqEUKL0sboM9mLpM74Uf0
a6pJ8crla3jSKqw7r9hbIONYsvrRlBxbbBkHBS9Td9X0+Dvoj3tr1tKhNld/Cr0v
bi/FfgLH60Vmkn5lwWGCmDE6IvpzkSo1O0yFA9GiDdfiZlkLcdAvUCkHjCsY11Qf
0z2FYQKBgQDCbtiEMMHJGICwEX2eNiIfO4vMg1qgzYezJvDej/0UnqnQjbr4OSHf
0mkVJrA0vycI+lP94eEcAjhFZFjCKgflZL9z5GLPv+vANbzOHyIw+BLzX3SybBeW
NgH6CEPkQzXt83c+B8nECNWxheP1UkerWfe/gmwQmc0Ntt4JvKeOuw==
-----END RSA PRIVATE KEY-----
"""

KEY2 = """
-----BEGIN PRIVATE KEY-----
MIIEpAIBAAKCAQEAxGSOx4CjDp4f8iBZvnMPjtBEDQ2j2M2oYvqidFJhoyMJMpy7
dPWc9sFNWXFJDD1xqHZqdegloVnMhxztzRE8YyklHfBV7/Sw4ExN4PQIUfB2GKfa
WjvkAwuV1z/up6e4xP1vFpApncwNFtqXP4RIhcVk/H87LZynm9bCrc4RABxHAyF1
hl9GOgpn7FD6QeF0kPgFpqR57y/I/ajdP7EtjZk4EEu26HKkH3pCsIRKjMvy7ZhL
cOpurVfSB7R65v+WT5AwOOu0XmRMLjmOAkTKR1EWGArOc7kgDCce3k29nXBDEX+U
C+3qUEbm31e4VXVxA4uITsHOSUOM5f3s7L0nEwIDAQABAoIBAQCxBnt09U0FZh8h
n2uFsi15690Lbxob2PVJkuZQt9lutawaxRBsEuETw5Y3Y1gXAmOrGGJKOaGB2XH0
8GyiBkFKmNHuNK8iBoxRAjbI6O9+/KNXAiZeY9HZtN2yEtzKnvJ8Dn3N9tCsfjvm
N89R36mHezDWMNFlAepLHMCK7k6Aq2XfMSgHJMmHYv2bBdcnbPidl3kr8Iq3FLL2
0qoiou+ihvKEj4SAguQNuR8w5oXKc5I3EdmXGGJ0WlZM2Oqg7qL85KhQTg3WEeUj
XB4cLC4WoV0ukvUBuaCFCLdqOLmHk2NB3b4DEYlEIsz6XiE3Nt7cBO2HBPa/nTFl
qAvXxQchAoGBAPpY1S1SMHEWH2U/WH57jF+Yh0yKPPxJ6UouG+zzwvtm0pfg7Lkn
CMDxcTTyMpF+HjU5cbJJrVO/S1UBnWfxFdbsWFcw2JURqXj4FO4J5OcVHrQEA6KY
9HBdPV6roTYVIUeKZb6TxIC85b/Xkcb3AHYtlDg3ygOjFKD6NUVNHIebAoGBAMjT
1bylHJXeqDEG+N9sa1suH7nMVsB2PdhsArP3zZAoOIP3lLAdlQefTyhpeDgYbFqD
wxjeFHDuJjxIvB17rPCKa8Rh4a0GBlhKEDLm+EM3H0FyZ0Yc53dckgDOnJmyh9f+
8fc7nYqXEA7sD0keE9ANGS+SLV9h9v9A7og7bGHpAoGAU/VU0RU+T77GmrMK36hZ
pHnH7mByIX48MfeSv/3kR2HtgKgbW+D+a47Nk58iXG76fIkeW1egPHTsM78N5h0R
YPn0ipFEIYJB3uL8SfShguovWNn7yh0X5VMv0L8omrWtaou8oZR3E2HGf3cxWZPe
4MNacRwssNmRgodHNE2vIr8CgYABp50vPL0LjxYbsU8DqEUKL0sboM9mLpM74Uf0
a6pJ8crla3jSKqw7r9hbIONYsvrRlBxbbBkHBS9Td9X0+Dvoj3tr1tKhNld/Cr0v
bi/FfgLH60Vmkn5lwWGCmDE6IvpzkSo1O0yFA9GiDdfiZlkLcdAvUCkHjCsY11Qf
0z2FYQKBgQDCbtiEMMHJGICwEX2eNiIfO4vMg1qgzYezJvDej/0UnqnQjbr4OSHf
0mkVJrA0vycI+lP94eEcAjhFZFjCKgflZL9z5GLPv+vANbzOHyIw+BLzX3SybBeW
NgH6CEPkQzXt83c+B8nECNWxheP1UkerWfe/gmwQmc0Ntt4JvKeOuw==
-----END PRIVATE KEY-----
"""

CERTIFICATE = """
-----BEGIN CERTIFICATE-----
MIIC9zCCAd8CAmlJMA0GCSqGSIb3DQEBBQUAMG4xCzAJBgNVBAYTAlVTMRAwDgYD
VQQIEwdBbGFiYW1hMRMwEQYDVQQHEwpIdW50c3ZpbGxlMRYwFAYDVQQKEw1SZWQg
SGF0LCBJbmMuMSAwHgYJKoZIhvcNAQkBFhFqb3J0ZWxAcmVkaGF0LmNvbTAeFw0x
MTA2MDMyMDQ5MjdaFw0yMTA1MzEyMDQ5MjdaMBQxEjAQBgNVBAMTCWxvY2FsaG9z
dDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMRkjseAow6eH/IgWb5z
D47QRA0No9jNqGL6onRSYaMjCTKcu3T1nPbBTVlxSQw9cah2anXoJaFZzIcc7c0R
PGMpJR3wVe/0sOBMTeD0CFHwdhin2lo75AMLldc/7qenuMT9bxaQKZ3MDRbalz+E
SIXFZPx/Oy2cp5vWwq3OEQAcRwMhdYZfRjoKZ+xQ+kHhdJD4Baakee8vyP2o3T+x
LY2ZOBBLtuhypB96QrCESozL8u2YS3Dqbq1X0ge0eub/lk+QMDjrtF5kTC45jgJE
ykdRFhgKznO5IAwnHt5NvZ1wQxF/lAvt6lBG5t9XuFV1cQOLiE7BzklDjOX97Oy9
JxMCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEAZwck2cMAT/bOv9Xnyjx8qzko2xEm
RlHtMDMHpzBGLRAaj9Pk5ckZKJLeGNnGUXTEA2xLfN5Q7B9R9Cd/+G3NE2Fq1KfF
XXPux/tB+QiSzzrE2U4iOKDtnVEHAdsVI8fvFZUOQCr8ivGjdWyFPvaRKI0wA3+s
XQcarTMvR4adQxUp0pbf8Ybg2TVIRqQSUc7gjYcD+7+ThuyWLlCHMuzIboUR+NRa
kdEiOVJc9jJOzj/4NljtFggxR8BV5QbCt3w2rRhmnhk5bN6OdqxbJjH8Wmm6ae0H
rwlofisIJvB0JQxaoQgprDem4CChLqEAnMmCpybfSLLqXTieTPr116nQ9A==
-----END CERTIFICATE-----
"""

BUNDLE = ''.join((KEY,CERTIFICATE))
BUNDLE_ROOT = '/tmp/pulp/bundle-testing/test.crt'
CRTFILE = os.path.join(BUNDLE_ROOT, 'test.crt')


class TestBundles(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        if os.path.exists(BUNDLE_ROOT):
            shutil.rmtree(BUNDLE_ROOT)

    def tearDown(self):
        testutil.PulpAsyncTest.tearDown(self)
        if os.path.exists(BUNDLE_ROOT):
            shutil.rmtree(BUNDLE_ROOT)
            
    def testSplit(self):
        key, crt = Bundle.split(BUNDLE)
        self.assertEqual(key.strip(), KEY.strip())
        self.assertEqual(crt.strip(), CERTIFICATE.strip())
        
    def testJoin(self):
        bundle = Bundle.join(KEY, CERTIFICATE)
        print bundle
        self.assertTrue(KEY.strip() in bundle)
        self.assertTrue(CERTIFICATE.strip() in bundle)
        
    def testVerify(self):
        self.assertTrue(Bundle.haskey(KEY))
        self.assertTrue(Bundle.haskey(KEY2))
        self.assertFalse(Bundle.hascrt(KEY))
        self.assertTrue(Bundle.hascrt(CERTIFICATE))
        self.assertTrue(Bundle.hascrt(CERTIFICATE))
        self.assertTrue(Bundle.hasboth(BUNDLE))

    def testWrite(self):
        b = Bundle(CRTFILE)
        b.write(BUNDLE)
        f = open(CRTFILE)
        s = f.read()
        f.close()
        self.assertEqual(BUNDLE.strip(), s.strip())
        
    def testRead(self):
        b = Bundle(CRTFILE)
        b.write(BUNDLE)
        s = b.read()
        self.assertEqual(BUNDLE.strip(), s.strip())
