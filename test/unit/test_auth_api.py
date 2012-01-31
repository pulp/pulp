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

# Python
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.server.auth import principal
import pulp.server.auth.cert_generator as cert_generator
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server.auth.certificate import Certificate


SerialNumber.PATH = '/tmp/sn.dat'

CERT_DIR = '/tmp/test_repo_cert_utils/repos'
GLOBAL_CERT_DIR = '/tmp/test_repo_cert_utils/global'

CA = \
"""
-----BEGIN CERTIFICATE-----
MIIFnTCCA4WgAwIBAgIJAMH9nQr2GQwCMA0GCSqGSIb3DQEBBQUAMGUxCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQK
DAdSZWQgSGF0MQ8wDQYDVQQLDAZQdWxwIDExEjAQBgNVBAMMCXB1bHAtY2EtMTAe
Fw0xMTAzMjUxOTUwNTlaFw0xMjAzMjQxOTUwNTlaMGUxCzAJBgNVBAYTAlVTMQsw
CQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQKDAdSZWQgSGF0
MQ8wDQYDVQQLDAZQdWxwIDExEjAQBgNVBAMMCXB1bHAtY2EtMTCCAiIwDQYJKoZI
hvcNAQEBBQADggIPADCCAgoCggIBANwv8xjqslOq+651JLjoKrIVx6H/wcpYlvWH
1Bhy+H0THOoNlfBXKt9WHsjx5DzDBokEUC6MwaG673vrMOepLjAbLz1h0weEtj0Y
xlrGY4vXwhB0hDrIHqSf+oGcYkJur1M5Mz76Ucfm7hNn/kYC8JznLR1X/GhBPoeZ
XHzSBn070BMBk68Y46DVfQJKQfnlAJaoEetO6++w1MFZGzZS33AEW3hDsHQ75OoX
IpM7A17rfO5HzdBaHHHhMwcuG8hlJxAroXiCLa3CziGo0seAWPkCSDX6Eo7/GhDR
ewP3+PH4r0oFjbJj60onR5ONznHbVUcMHhLWlQzo0vnwrr3sRt49KOjsBD6CKVlo
LHo1b6khcuxBcAM2uyC45HhTIZIjBX79E3OEMhnDMHct3RLj9dP2ww+foz2+5iay
dPvCdLGAQ0UD3unaipHiWU551EEUTpstyGUO9A2uN8+R67SHcTvkxbgvTJZ9ytpV
RotZ6e41SjDBEj6Y+cEQsDciU0xk6WN3aII01F2J+lREB529wlEi582SP4UMErQH
NF4VEiHFCKn+MlkJ2BbYZA5V8SrbtNq2Rf0jXKUlcc9rqKCHmBDuUDYQoddwcgNe
d+ecwjbUWjBaB1CG3NEb6Jro7JjtFgE5D6FkChkb94qpmcLjViEKP+TvZYhqhLBT
AczTQe1dAgMBAAGjUDBOMB0GA1UdDgQWBBSE7cYaW9SXLeJOP3fyi0knZo4WLjAf
BgNVHSMEGDAWgBSE7cYaW9SXLeJOP3fyi0knZo4WLjAMBgNVHRMEBTADAQH/MA0G
CSqGSIb3DQEBBQUAA4ICAQDLNtVSUZfFbaqMF78MwWyrKqhDDo6g1DHGTqOYxK+v
jBkNPIdOFDEJzxVcRFCs2puKH4lHU+CfJo4vDbQ93ovXBWVACjS/pX0FJQ1e10oB
Ky3Lo6fuIjecO6Y2eoTWNadJkcjyrhcDKDOHaZb5BBFS3Lx8F37U9TGsy47jNS+x
l0wfCBeydNzEY4pYXPxMK/3TY48WM8pSn5ML/rrD3Em1Omt86pYW98DNB1Ibqc1Y
614qYPzStEYxXcg5fkIJBliVZmruKutGc3EzTQwa9E/UKN3zFfWfOYSl6Hgo7UKS
gAYHhQm6/6jREGgSFDG9bQa4qEMNLrYc1cWYm9daKoAhVfJ3Cm8GYdyeD2mDh/n6
p3k8fqdOs5hKYCgusUDgdZ4B5nC7H05vVnCXVyfwN5zRb3NxgjkPlgClOdvlsrTT
dFLor0h7zsSC7tV+0LVItwqWl6b6v6AutRJz1Q0H7NPWw96yQodX2Tl/1IOtM2j1
qkbOzF1i1H/SQ22dHLT2ayT+Zz84okUtTN417+Rn2tvUTmDMbPft28LmzguItw1e
ySWfIQ51GrBhqUH8qI1UfCduu/QA/sHT0pmKmxIzchZH9/kCyZRFPG7+OzDyj/Dx
3xYZYYqU3eMSvj72/hifSZtipT1qWkxpAdSz9c9ZGZXeiZUl/23UyeGq1qp7wU+k
Hg==
-----END CERTIFICATE-----
"""

KEY = \
"""
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

CERTIFICATE = \
"""
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

class TestAuthApi(testutil.PulpAsyncTest):

    def clean(self):
        testutil.PulpAsyncTest.clean(self)
        if os.path.exists(CERT_DIR):
            shutil.rmtree(CERT_DIR)
        if os.path.exists(GLOBAL_CERT_DIR):
            shutil.rmtree(GLOBAL_CERT_DIR)

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.config = testutil.load_test_config()
        self.config.set('repos', 'cert_location', CERT_DIR)
        self.config.set('repos', 'global_cert_location', GLOBAL_CERT_DIR)
        self.repo_cert_utils = RepoCertUtils(self.config)
        sn = SerialNumber()
        sn.reset()

    def test_admin_certificate(self):
        # Setup
        admin_user = self.user_api.create('test-admin')
        principal.set_principal(admin_user) # pretend the user is logged in

        # Test
        cert = self.auth_api.admin_certificate()

        # Verify
        self.assertTrue(cert is not None)

        certificate = Certificate(content=cert)
        cn = certificate.subject()['CN']
        username, id = cert_generator.decode_admin_user(cn)

        self.assertEqual(username, admin_user.login)
        self.assertEqual(id, admin_user.id)

    def test_enable_global_repo_auth(self):
        '''
        Tests that enabling global repo auth correctly saves the bundle and informs
        the CDS instances of the change.
        '''

        # Setup
        bundle = {'ca' : CA, 'key' : KEY, 'cert' : CERTIFICATE, }

        # Test
        self.auth_api.enable_global_repo_auth(bundle)

        # Verify
        read_bundle = self.repo_cert_utils.read_global_cert_bundle()

        self.assertTrue(read_bundle is not None)
        self.assertEqual(read_bundle, bundle)

    def test_disable_global_repo_auth(self):
        '''
        Tests that disabling global repo auth correctly removes the bundle and informs
        the CDS instances of the change.
        '''

        # Setup
        bundle = {'ca' : CA, 'key' : KEY, 'cert' : CERTIFICATE, }
        self.auth_api.enable_global_repo_auth(bundle)

        # Test
        self.auth_api.disable_global_repo_auth()

        # Verify
        read_bundle = self.repo_cert_utils.read_global_cert_bundle()
        self.assertTrue(read_bundle is None)
