#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

# Python
import shutil
import sys
import os
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.repo_auth import oid_validation, repo_cert_utils
import testutil

# -- constants ------------------------------------------------------------------

CERT_TEST_DIR = '/tmp/test_oid_validation/'

# -- mock functions -------------------------------------------------------------

def log(message):
    pass

# -- test cases -----------------------------------------------------------------

class TestOidValidation(unittest.TestCase):

    def setUp(self):
        override_file = os.path.abspath(os.path.dirname(__file__)) + '/../common/test-override-repoauth.conf'
        repo_cert_utils.CONFIG_FILENAME = override_file

        if os.path.exists(CERT_TEST_DIR):
            shutil.rmtree(CERT_TEST_DIR)

    def tearDown(self):
        if os.path.exists(CERT_TEST_DIR):
            shutil.rmtree(CERT_TEST_DIR)
    
    def test_global_enabled_passes_global(self):
        pass

    def test_global_enabled_fails_global(self):
        pass

    def test_individual_enabled_passes(self):
        pass

    def test_individual_enabled_fails(self):
        pass
    

# -- test data ---------------------------------------------------------------------

# Entitlements for:
#  - epos/pulp/pulp/fedora-14/x86_64/
CLIENT_CERT = '''
-----BEGIN CERTIFICATE-----
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
I9bmz1dqBo2/e4UnBko=
-----END CERTIFICATE-----
'''

VALID_CA = '''
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
'''

INVALID_CA = '''
-----BEGIN CERTIFICATE-----
MIIFnTCCA4WgAwIBAgIJAII71LRLCAczMA0GCSqGSIb3DQEBBQUAMGUxCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQK
DAdSZWQgSGF0MQ8wDQYDVQQLDAZQdWxwIDIxEjAQBgNVBAMMCXB1bHAtY2EtMjAe
Fw0xMTAzMjUyMDA0MTBaFw0xMjAzMjQyMDA0MTBaMGUxCzAJBgNVBAYTAlVTMQsw
CQYDVQQIDAJOSjESMBAGA1UEBwwJTWlja2xldG9uMRAwDgYDVQQKDAdSZWQgSGF0
MQ8wDQYDVQQLDAZQdWxwIDIxEjAQBgNVBAMMCXB1bHAtY2EtMjCCAiIwDQYJKoZI
hvcNAQEBBQADggIPADCCAgoCggIBALIZrAAZFxKqzpMXiIwClv/o1tyFn6hnUhEX
HXaCHoY5QZZ695UXz9b0dxNKaMgfEq9fjfdP3f8A1yg9lTIyiG4BAPpSla/RT/B6
fBwLF2WBvCbPJB7w5+ZLCHkDIOd6swBQUEHXGOIEk1IUByEndlksHzzUpVL8BDq4
gMfDCmsV5SsfcQN8ophgXN6fOPHtluOmfIjxoCq69aB0NjjDzYbW9Vo/2VLeNbdv
XEfZRBgJv/VpSAQF8POB3yHUw95GN5OjECXhMBQ2mlyyNksVSFIn2yOBwr7tejVA
61pjZio1CMN5JLc63DZQkBNEtGknG6qmcVhZUjhINsK5R1S/Mh3oyT9/c1W+yPii
oJOe7PEemlWSwt4ufFnXbRMbUDx9g0ud6nUxnXPA9RugkfkXvsXKct4ql1WI64jL
3sDUNN65aj8W8LG+WOEYuXvuyXkFl/lMT9wzLG9Y85xB6S1wnggS/4zVikptHEFK
KjLOlCWYPQNmbjUiekkRk/qnAixTqLcNXssVj4GlW9ElZeu4mNidk/lXoeVzyIBJ
710OjUH7EuMe87gPf3q0x/Cm6E98O6b9Zqhm6/4nQSrd1YT5kqRfCWMyKP8bdSpU
HAT6Zx3b1df4mdZZ6JW7MF5cXHaGxZzdA7WVpq6YAg7JJxBt9B2KOQyj1kXOeWuD
RU1qIJCtAgMBAAGjUDBOMB0GA1UdDgQWBBT2RGJP7ERHn5q5rR7gOsfybW5zMDAf
BgNVHSMEGDAWgBT2RGJP7ERHn5q5rR7gOsfybW5zMDAMBgNVHRMEBTADAQH/MA0G
CSqGSIb3DQEBBQUAA4ICAQBI2Yi0q2S2giGy/banh3Ab3Qg1XirkGa3HmA2JF7XV
dcsPjzDwKd3DEua76gZ94w+drEve0z95YPC02jiK2/9EOyoIS+Sc3ro698mUuUuY
A0vxAQJEoQNlCtNs7St60L98wWp64oTiTPTBjYBoQsBYul9Omh/qkmMqz/L/t47T
nc3AcVzrDwesNlyWUMPg1SajXth4ux6+7/GiWaE8QRZiX6LjN6362dN8J7P39iBj
Ftw1duPZTYg5gkmuYjy+CfSvSyzq/TKV5JYVWijpAzAM9iyoBQFLEfzA8Vb+C+kk
DTKhBObJF1aGxJHFkIqN2XnKaBAQYzR3y7duUJS7OmufSVwsJgzT1jUCZ/qFLFlW
TSiSdWGGR2NzsMoO4mCLBFpHe2PENFy//US1OQERNBHZKFx3t8YyLh8tzda5goXM
4K+FIH1+WeoibKr+UnQC4CU3Ujbf3/Ut7+MDu5A76djkPjgIbJChe3YoExBzJck3
DAK56kpnnuqwj0EyAqpsEiF4CAcpBwLP7LVc68XGfzIzRaRJOlerEscFR2USmW+c
+ITpNVXEGdZgdBjIIq/n+59JqEHnKinRaQMZBNppD6WZ6NVelcb4094kc1H1Qpkt
f/LU796X0sQbbbpuKab4CNNYaj7ig5wnbC5ONYmYTebcOML+H9b/iOomNCPDmLpj
tA==
-----END CERTIFICATE-----
'''