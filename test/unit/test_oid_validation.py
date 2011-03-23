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
import sys
import os
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.repo_auth import oid_validation, certificate
import testutil

# -- test data ---------------------------------------------------------------------

# Download URL in the following:
#  content/dist/rhel/server/5Server/$basearch/os
ENTITLED_CERT = '''
-----BEGIN CERTIFICATE-----
MIIFGDCCAwCgAwIBAgIBYzANBgkqhkiG9w0BAQUFADCBkDELMAkGA1UEBhMCVVMx
FzAVBgNVBAgMDk5vcnRoIENhcm9saW5hMRAwDgYDVQQHDAdSYWxlaWdoMRAwDgYD
VQQKDAdSZWQgSGF0MRowGAYDVQQLDBFDbG91ZGUgRW5hYmxlbWVudDEoMCYGA1UE
AwwfQW1hem9uIERldmVsb3BlciBFbnZpcm9ubWVudCBDQTAeFw0xMDA3MjYyMTA0
NDNaFw0xMDA4MjUyMTA0NDNaMBQxEjAQBgNVBAMMCTEyMzQ1Njc4OTCCASIwDQYJ
KoZIhvcNAQEBBQADggEPADCCAQoCggEBAKTSXY4oYyunJDFbUjdvrnqFvlPp/sQc
68SesPkRIDehYuzWgIdsktEZM1Fm6vTrAZQZ6jSogibni80ub2ejySJIAbEdwD/n
417rrABJkSKoVXwzbKisIZA35EvXBu0D3Fpr/202pF8lHG0f0rIc3CR8MBUNRMAh
N6qBwGfs3NHAJkzVii8Y/wRb1b0iwZ14Xy/Cq4rpkZmM0PMTBnd/eA4mLDPWh4y7
zQ3bu7NTlTNB3/GelP9iZrFFIZqVFQGnMM+sIjX0BUFqd3oWziDExZMVr4dWSf9+
PeslYxpBHFHWg/M4y80xLzsG+ZUzlideREac13nBVaL64LnqJeq4WP0CAwEAAaOB
9zCB9DAJBgNVHRMEAjAAMCsGDSsGAQQBkggJAohXAQEEGgwYUmVkIEhhdCBFbnRl
cnByaXNlIExpbnV4MBkGDSsGAQQBkggJAohXAQIECAwGcmhlbC01MEAGDSsGAQQB
kggJAohXAQYELwwtY29udGVudC9kaXN0L3JoZWwvc2VydmVyLzVTZXJ2ZXIvJGJh
c2VhcmNoL29zMB4GDSsGAQQBkggJApEuAgEEDQwLUmVkIEhhdCBJU08wGwYNKwYB
BAGSCAkCkS4CAgQKDAhyaGVsLWlzbzAgBg0rBgEEAZIICQKRLgIGBA8MDXNvbWUt
aXNvLWZpbGUwDQYJKoZIhvcNAQEFBQADggIBAEaemI2I0C7B8ml/+eJ62OrMiHr9
y8Wo52VPILjckRfy9CumREtVDPqfu6U3M6HWSwZYeUtkxbzi6QoQ0GuwfUAdiZdi
9U7L2kKJwoyK4P9MNaa0NogVAFOXjsgLWA3SRdQRk6SdoGDrIdsPnDD2EvGI11QL
QYMQZAIpXrP6WFCp3IT95uT2tvX/b6A5mp3KubacJPMdYfdpT//6CU2iKMjUhRZ8
YA2u8NSobFx3VCdz6ugGElg8lppajLak8LdMjl5zIJkowNNhyxX4K1SbIfChW51y
jhW4DXatuq9XF8ZJFDgLGBku7q6W2eTlPCPrywwNjLkk6yA7ogSQmCOvifz3n2xL
fMoCCz05E8CV4tjGWhiLycBPAbsaBJrM/B4L7BzhKGgdOkXQX/T2EKv3C56DXH7s
0LfNbMgyAy5lO4M5J6LlythfvblNKZSmY6HfIGlN8bKysvQgY6wxlIpYzJq5+uWY
5SzNIa0ZtSpVzCjtESsLXhOSS5jed1Dvs+u60CWxZrtPPAk3f/pUSgTaixeymvAP
b2BCFVZT4+BQS+GjzHUGNLRFyowgjJ2Mf6c7SuBE1YoHzycXS8ZEM+VxiZwIR46w
MWJhY5AgLbikKZ5G9iOtauud6WTB8jHRiGPdz1huAVg89HpUlOKU+hNYM+lpyDxE
Je08DRSLeHSysFed
-----END CERTIFICATE-----
'''

UNENTITLED_CERT = '''
-----BEGIN CERTIFICATE-----
MIIEHjCCAgagAwIBAgIBYzANBgkqhkiG9w0BAQUFADCBkDELMAkGA1UEBhMCVVMx
FzAVBgNVBAgMDk5vcnRoIENhcm9saW5hMRAwDgYDVQQHDAdSYWxlaWdoMRAwDgYD
VQQKDAdSZWQgSGF0MRowGAYDVQQLDBFDbG91ZGUgRW5hYmxlbWVudDEoMCYGA1UE
AwwfQW1hem9uIERldmVsb3BlciBFbnZpcm9ubWVudCBDQTAeFw0xMDA3MTIyMDM4
MzlaFw0xMDA4MTEyMDM4MzlaMBQxEjAQBgNVBAMMCTEyMzQ1Njc4OTCCASIwDQYJ
KoZIhvcNAQEBBQADggEPADCCAQoCggEBAKTSXY4oYyunJDFbUjdvrnqFvlPp/sQc
68SesPkRIDehYuzWgIdsktEZM1Fm6vTrAZQZ6jSogibni80ub2ejySJIAbEdwD/n
417rrABJkSKoVXwzbKisIZA35EvXBu0D3Fpr/202pF8lHG0f0rIc3CR8MBUNRMAh
N6qBwGfs3NHAJkzVii8Y/wRb1b0iwZ14Xy/Cq4rpkZmM0PMTBnd/eA4mLDPWh4y7
zQ3bu7NTlTNB3/GelP9iZrFFIZqVFQGnMM+sIjX0BUFqd3oWziDExZMVr4dWSf9+
PeslYxpBHFHWg/M4y80xLzsG+ZUzlideREac13nBVaL64LnqJeq4WP0CAwEAATAN
BgkqhkiG9w0BAQUFAAOCAgEAPnScHvZc8JCIq9uavmseu3KrToUobXdaJnxx2YS7
c5xlF4pa/htcAsNnIqBHMi1DZgAbeAxeJLzkQmMR6UTKvXNTy90ye3jiZvoAYCau
OiU36wVLhuz8VOdiESQMzkCjbgqep9G53J6Qq/oqSXTkeac6ND7GlSrvRF9U5SCe
IVPqO1xJ+2dx9fE1a0X7OqkyNM7bHV8R4b1XLpAuseWPI0i3YdrPyxuFbZvcbokT
KvPRrlhxC2/KJ2JCqYeO9rnwv1lf/370p6oe3EREcUvptw24N016VYFz1HC9WaFB
YZZKdRN25TqHjtomg1+SzqUaDTaLYzOTRiVqeqTTFOP+2pM+qGaik3f2j2rLcD/H
QmeTyp4ppA/sz9FkwdzaKDME6dT0jxzZO5EprmFEj2t7oZiSd7plnbE8qZWgw8zQ
vcdwQk+I7isJlSSWS14cP/o8vtCj1pLRqvrXFzLXpHcsqoJvSwSPEUGO6+6fXZrF
PRCoAaz5YRGlgrLA/dDy839vuuKhrzL+6A1mBjVGesnWIOT4h2px5OJWK2bvpOi7
BD6woIhmP22WSB6jenpwXhEImkz85cU0niIiHERWETM80FPUOVkKndUdqHU6WxY2
UJP5Qzc6IrHxHMhb3t6zppNOR76aZ/S5nY5n3vpMGlPPWXfTZS7z0sl5zu2Gz0SZ
cTI=
-----END CERTIFICATE-----
'''

IDENTITY_CERT = '''
-----BEGIN CERTIFICATE-----
MIIEHTCCAgUCAQEwDQYJKoZIhvcNAQEFBQAwgZAxCzAJBgNVBAYTAlVTMRcwFQYD
VQQIDA5Ob3J0aCBDYXJvbGluYTEQMA4GA1UEBwwHUmFsZWlnaDEQMA4GA1UECgwH
UmVkIEhhdDEaMBgGA1UECwwRQ2xvdWRlIEVuYWJsZW1lbnQxKDAmBgNVBAMMH0Ft
YXpvbiBEZXZlbG9wZXIgRW52aXJvbm1lbnQgQ0EwHhcNMTAxMTA4MTI1NDIxWhcN
MTExMTA4MTI1NDIxWjAYMRYwFAYDVQQDEw1yaHVpLWlkZW50aXR5MIIBIjANBgkq
hkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwTOU+Al6d7duCx1Ksaj9GoEMtQLjzwWH
WB+WYFiN+RuXazGn13jJ6MhxoyEnbHsOrJbyl/DCSGF+1CppZ6UZqKBsa+Og9lDt
GXL3Zyw8a4aimRDP7LDR3FUsYx1SNU/O+jpwh1SW9bskQv4uSYAoxDPHlDaGadUL
Cv0trpws3ENGNuJviAvYF4czusvIOstpnnNVEgEQNdM2ZLzyck+BdTo/LQAOrDRj
ixCEfm85npyLD2D432CiFzCAhkfkkAEpq0EEopL16BVvD+eFYO0cR9ME8HlWJhFn
I4vFsXZvai5bYmT/lS25sLKeitsmdU08HOru1of9zGr6QycUD5sqLQIDAQABMA0G
CSqGSIb3DQEBBQUAA4ICAQB57dY2efK6cX8kJ3fQZUVrAgNuSrTy8Zm/4XIKsLS7
JZ7BzGJpH2AhC86F3+tYDtLpg/7us4pDoKuuV22ihjfGSMEPhCXb4d7jEM0qRYCD
bZUN8XGpZELeynfGZaNy/502UZjodVVgOXoi4jNiwipG26L5chkIzwgH68/l7Iv4
UlCLGzAJvVv6mW44zNrNjsSEqD0bvFQsqQv9EMjQozlnT4bkG11BMBJw8H8EQAYi
ZWsrY1IL6Yh9+o6Y+MRBbGMaCD2LBDSZsEDuJik/nPRwOQVlCpPfOeo987CslAPn
3XoJEeaifgDb07Vavt2c23xfWhbA5jsv5d4juunsAy2QjEFvQ2vKOI9Eq7f9WL7b
wJwPZ2eUHFCcSFUMqwpoBm/BiEDF8uLYkdSbStUMWi1C7fU3PnFC8955dpZrko8L
66d2/yzSJHZD2vOawNoS+SrB1TJE26c/VqhvwMbw+hvl+QKoolekGqKhjXpyUEC0
hJh2tDeP2UsXoHO1ZXAIVl/HWOr2IzPLyywYRgFJlJfI0citTW2KnPTzQPE/doYI
s9ZiW5vAQnVJQlAL6UG1oFdI/pubCuU7pV3+p+k6l3VTfzz0qYYpNdK/Ew3OnvTS
rP5gT6Y5qC9tKL8/fIzUB1GfY/JQGsEW0jH0I5VvA6GntFh4n8AIZ1bRFH4fhXm0
tg==
-----END CERTIFICATE-----
'''

# -- mock functions -------------------------------------------------------------

def log(message):
    pass

# -- test cases -----------------------------------------------------------------

class TestOidValidation(unittest.TestCase):

    def test_is_download_url_ext(self):
        # Test
        self.assertTrue(oid_validation._is_download_url_ext(certificate.OID('1.3.6.1.4.1.2312.9.2.1111.1.6')))
        self.assertTrue(oid_validation._is_download_url_ext(certificate.OID('1.3.6.1.4.1.2312.9.2.2222.1.6')))
        self.assertTrue(not oid_validation._is_download_url_ext(certificate.OID('foo')))

    def test_is_valid(self):
        # Test
        self.assertTrue(oid_validation._is_valid('content/dist/rhel/server/5Server/x86_64/os/', ENTITLED_CERT, log))
        self.assertTrue(oid_validation._is_valid('content/dist/rhel/server/5Server/i386/os/', ENTITLED_CERT, log))
        self.assertTrue(not oid_validation._is_valid('pub/repoX', ENTITLED_CERT, log))

        self.assertTrue(not oid_validation._is_valid('pub/repo1', UNENTITLED_CERT, log))
        self.assertTrue(not oid_validation._is_valid('pub/repo2', UNENTITLED_CERT, log))
        self.assertTrue(not oid_validation._is_valid('pub/repoX', UNENTITLED_CERT, log))

    def test_validate(self):

        # Zero Variables
        self.assertTrue(oid_validation._validate('content/dist/rhel/server/5Server/x86_64/os',
                                             '/content/dist/rhel/server/5Server/x86_64/os/repomd.xml'))

        self.assertTrue(not oid_validation._validate('content/dist/rhel/server/5Server/x86_64/os',
                                             '/content/dist/rhel/server/5Server/i386/os/repomd.xml'))

        # One Variable
        self.assertTrue(oid_validation._validate('content/dist/rhel/server/5Server/$basearch/os',
                                             '/content/dist/rhel/server/5Server/x86_64/os/repomd.xml'))

        self.assertTrue(oid_validation._validate('content/dist/rhel/server/5Server/$basearch/os',
                                             '/content/dist/rhel/server/5Server/i386/os/repomd.xml'))

        self.assertTrue(oid_validation._validate('content/dist/rhel/server/5Server/$basearch/os',
                                             '/content/dist/rhel/server/5Server/foo/os/repomd.xml'))

        # Multiple Variables
        self.assertTrue(oid_validation._validate('content/dist/rhel/server/$version/$basearch/os',
                                             '/content/dist/rhel/server/5Server/i386/os/repomd.xml'))

        self.assertTrue(oid_validation._validate('content/dist/rhel/server/$version/$basearch/os',
                                             '/content/dist/rhel/server/6Server/i386/os/repomd.xml'))

        self.assertTrue(oid_validation._validate('content/dist/rhel/server/$version/$basearch/os',
                                             '/content/dist/rhel/server/5Server/x86_64/os/repomd.xml'))

        # Make sure both variables need to be specified when two variables are adjacent to each other
        self.assertTrue(not oid_validation._validate('content/dist/rhel/server/$version/$basearch/os',
                                             '/content/dist/rhel/server/i386/os/repomd.xml'))
