#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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

import unittest

import pulp.webservices.httpd.repo_cert_validation as validation
import pulp.certificate

ENTITLED_CERT = '''
-----BEGIN CERTIFICATE-----
MIIE4zCCAsugAwIBAgIBYzANBgkqhkiG9w0BAQUFADBxMQswCQYDVQQGEwJVUzEV
MBMGA1UEBwwMRGVmYXVsdCBDaXR5MRwwGgYDVQQKDBNEZWZhdWx0IENvbXBhbnkg
THRkMQ0wCwYDVQQLDARQdWxwMR4wHAYDVQQDDBVmZWRvcmFob3N0ZWQub3JnL3B1
bHAwHhcNMTAwNzA5MTkyNjU3WhcNMTAwODA4MTkyNjU3WjAUMRIwEAYDVQQDDAkx
MjM0NTY3ODkwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQCk0l2OKGMr
pyQxW1I3b656hb5T6f7EHOvEnrD5ESA3oWLs1oCHbJLRGTNRZur06wGUGeo0qIIm
54vNLm9no8kiSAGxHcA/5+Ne66wASZEiqFV8M2yorCGQN+RL1wbtA9xaa/9tNqRf
JRxtH9KyHNwkfDAVDUTAITeqgcBn7NzRwCZM1YovGP8EW9W9IsGdeF8vwquK6ZGZ
jNDzEwZ3f3gOJiwz1oeMu80N27uzU5UzQd/xnpT/YmaxRSGalRUBpzDPrCI19AVB
and6Fs4gxMWTFa+HVkn/fj3rJWMaQRxR1oPzOMvNMS87BvmVM5YnXkRGnNd5wVWi
+uC56iXquFj9AgMBAAGjgeIwgd8wCQYDVR0TBAIwADAVBgorBgEEAZIIAwMBBAcM
BXJlcG8xMB8GCisGAQQBkggDAwIEEQwPRW50aXRsZWQgUmVwbyAxMBwGDSsGAQQB
kggJApoFAQYECwwJcHViL3JlcG8xMB8GCisGAQQBkggDAgEEEQwPRW50aXRsZWQg
UmVwbyAyMBwGDSsGAQQBkggJApEuAQYECwwJcHViL3JlcG8yMB8GCisGAQQBkggD
AQEEEQwPRW50aXRsZWQgUmVwbyAzMBwGDSsGAQQBkggJAohXAQYECwwJcHViL3Jl
cG8zMA0GCSqGSIb3DQEBBQUAA4ICAQCS29KnAuoeaQQUq+BoZT6vvbLzAhDTiKjn
n/nC1VHBVc+ywc1mmEWXrO4ZUIaKBXNJWKTnd7mzOzzKuAGhnUwMZF2qsf6x0M6F
k6derMEI2KDfbhuwyfzGc/nxdU36qOJ+8eMLS6s8F+oFM4suCyjBbfx7n/6QGSdS
oTDqg1xpffnDWQU0U62n04c8CbRAUXqIaFR1My+BDV73P0u1c5oBDZ8yUrzf3sn7
1XncjLAr2Wn+Nl18AIkRTpheb99ztwt7x3hCLO0LmHu+FhKVtH2GmisrHA62seYY
2sRSisWWEzi1c5lE8+NyJg9rIGnxWQArBSrCB4i0n4p9tDVPI/rpv6cTRCvrhwoy
zJuvxx+o3u4Fpvw14yoxLRR4UWSTONzmofVoLqUhIZ7TC28aZQkipNGUHW7zENkm
kk8XIvitTveyVzJo4et2LOvJaoVRHmbKJFc/j47qtd948JDgvXvQtQKK5SozeSRO
qgqmh52mKufqEyfT3Q80HLtpoe7vD0xDcXrnkPj9NNQgXsqSG68HqdQMJQ1tbKY4
yK8sQdmZUWbRlgGnYJqc/QnPdPaMptJwRHcJhzhGslIWbcQI/rpiPbNWepoBf1U2
ovtbiEm65tQF/SncP7cOOTGidRHq+yJK7dMd9vTJtVla1Xoad+9E58MChmidnTX5
9pjqal9Dzw==
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


class TestEntitlementCerts(unittest.TestCase):

    def test_is_download_url_ext(self):
        # Test
        self.assertTrue(validation.is_download_url_ext(pulp.certificate.OID('1.3.6.1.4.1.2312.9.2.1111.1.6')))
        self.assertTrue(validation.is_download_url_ext(pulp.certificate.OID('1.3.6.1.4.1.2312.9.2.2222.1.6')))
        self.assertTrue(not validation.is_download_url_ext(pulp.certificate.OID('foo')))

    def test_is_valid(self):
        # Test
        self.assertTrue(validation.is_valid('pub/repo1', ENTITLED_CERT))
        self.assertTrue(validation.is_valid('pub/repo2', ENTITLED_CERT))
        self.assertTrue(not validation.is_valid('pub/repoX', ENTITLED_CERT))

        self.assertTrue(not validation.is_valid('pub/repo1', UNENTITLED_CERT))
        self.assertTrue(not validation.is_valid('pub/repo2', UNENTITLED_CERT))
        self.assertTrue(not validation.is_valid('pub/repoX', UNENTITLED_CERT))
