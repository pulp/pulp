"""
This module contains tests for the pulp.server.common.openssl module.
"""
from unittest import TestCase

from pulp.server.common.openssl import Certificate


CA = """
-----BEGIN CERTIFICATE-----
MIICvDCCAaQCCQCqmUc+ni6LkTANBgkqhkiG9w0BAQUFADAgMR4wHAYDVQQDDBVs
b2NhbGhvc3QubG9jYWxkb21haW4wHhcNMTQwNzIzMTcwNTA1WhcNMzMxMDI2MTcw
NTA1WjAgMR4wHAYDVQQDDBVsb2NhbGhvc3QubG9jYWxkb21haW4wggEiMA0GCSqG
SIb3DQEBAQUAA4IBDwAwggEKAoIBAQC2RD5TIIfK2bbJTb/wdO1ohcjat5tXiJyX
j9o4bmo0en+ceCRwufLhaIVHhJA17+JxXwJKEx6b9KLPcYXFk5Wg9yTiC7Aqp8dc
zlJ+3K4nU1ZY/4Fx+FsCh/W7yVG1j59eL0CtbNnfKO2ieUOpKTxVvirK4bUZV6YQ
7EDrK/xRcHeY5YdN3tsBq7XVfqns2TACvecAoHHecp45oIsz3g8vttOicREXU8m+
r7ofawaww7LngZTI/b1lElmFDmoJ+RYD/FQiNRExVvNU+mdPhkUmCbrvTZsxHoQp
+M3VBeX1dIa7a5my/pz2vK6Q6qLgcwZ2az88BuU4vuPXhQzdmK/VAgMBAAEwDQYJ
KoZIhvcNAQEFBQADggEBALYpN+EBo2oGUg6lZEcLIMrceeRbzGV3QcRm342TxrZu
ewb2NlNexht0stqqDTN4q2ZusRglk3DR+RMh5XIvd9uq0GRKXVx6cxkbNYZdVRdA
b3FSb67Hr5rsApjtU5XkESzzwYKyyIidv3tLQyAW4k/HIm0c8Jjam0TWJ1JNgZiY
BmBgxx7TA0o/MfwdL/eZUUbHzdDTFeCLUo4PR9AoxNYaXxKnDDuUXqz3tCSKMbZI
9eD7zPZ3OGTtDMSrHvfPHMR0iwYA/fY73GBSD4gWB6m9Y2051n8Cfso9PwdCx+I3
eRI3njrU/r5WxeGAVqwFwsYW2sxrfoKyJ4NdjsnXvBk=
-----END CERTIFICATE-----
"""


VALID = """
-----BEGIN CERTIFICATE-----
MIICxjCCAa4CAkBcMA0GCSqGSIb3DQEBBQUAMCAxHjAcBgNVBAMMFWxvY2FsaG9z
dC5sb2NhbGRvbWFpbjAeFw0xNDA3MjMxNzA1MDVaFw0yNDA3MjAxNzA1MDVaMDEx
HjAcBgNVBAMMFWxvY2FsaG9zdC5sb2NhbGRvbWFpbjEPMA0GA1UECgwGY2xpZW50
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu9zJOwEJWYkxwAJhS3SC
R+ew34J3Aii3FZWqZZVmxXvh+2brKpATcIgz022rlvujQveFHKH0909nQHAvTpiK
EOQN2OToDPY/f1T36nGPcd3TOdgPj8mB3sOYgsdrRCsPuL254Xc9uyO13tVbLQ93
5yXsZAuO4JkIi1W0kA9345w7aBPPF6erBQtG7BVV/36wWS0E8KfowYa5ImGVsxXz
ZwX9uADQYhCu3KJXbdgLt9UpdotOI7l0UvdlihPO2dQ3sX8iiNBs5aO9I5ArlyNV
RHqF2gHsIji7rcYXU33xV3P50seCmhNqmIr0Jsoy1SFhyRK/TgrSiTL5U7xfzPkO
fQIDAQABMA0GCSqGSIb3DQEBBQUAA4IBAQCT90KWczxwKCTScvhktBwtGL+5K/S3
YKyvzGCLIltcbPVV9HgJsspd/u/xfOX2/+pbMfJzr4XF+1Nd6bCk1clAIV9N26Nr
p5A9vunsKJfSwaBjZHWTv++C4+B+GHel4xe6jp7T67qBTAOatspuGgvJck0iQNyk
X/tYIxeoEC7FhwmZ+UzJCkJAS5qVI1I3LH+yS993EdVvsYNyJZWV9VN/pY3OshpS
+CZ/tTz68h1H6rmP5fBFrOPekQoo6AxYai3TnUILTlY9S9yb2cifIfhWfmmyIgwJ
3i1MZBZmStHzg/N3H0k3jnV+YLN8W+cMJgN8bCZBJonmA2VjbCAjvXcH
-----END CERTIFICATE-----
"""

INVALID = """
-----BEGIN CERTIFICATE-----
MIICUzCCATsCAQcwDQYJKoZIhvcNAQEFBQAwKDEXMBUGA1UEAwwOUHVscCBTZXJ2
ZXIgQ0ExDTALBgNVBAoMBFBVTFAwHhcNMTQwNzE3MTc0MjAxWhcNMjQwNzE0MTc0
MjAxWjA7MQ8wDQYDVQQDEwZqb3J0ZWwxKDAmBgoJkiaJk/IsZAEBExg1M2M4MGFl
OWUxMzgyMzc5YTBhYzIwYmYwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAOdM
Mmo1iGXqZ5lLvcERIJqkIcjGPI7ENe8wfgsH6V5bB5izq3apm++VIFqFsqjc79Fh
MInkMKqwQkL625ct/jtvUplluBXkamW49206P/GhZ2x/zvYpj9zFHhrzv3cN4J5+
ivHPM2DlQidZcefyDNuLYtKYgZqhpff0RR94CrvRAgMBAAEwDQYJKoZIhvcNAQEF
BQADggEBAGlt+3Bsqd2yw0Rm8lbYqLoWIdB+MtUQQGBSO1NpWHAdxO43maRzH23B
yZfVX7UQruhRQBAKm5sz8aN7d23Ab3b4YoQ2XZ3h5Kv2KIx2Dz+zCxgcr76ovPza
3CTbx7/xk+xizhi2C3twidu4U1zeTDBgHmACRv2IhadWggQZID1o5jt5+ZbBDGku
KBx1L4Q8Jsj0/SW9mikURIlRTDCl74bPVDbFJfhiC4dghUhUsO9UmLef19kNZoQO
Auku7zwCaSUMQ914lEvFtmMO77WR8TfPTh4k3vbKSb2ZtRQYeBb5QrsEYOXBmsxV
55enkvuG4KG6KgWXmvLuF3vCqOt3RUs=
-----END CERTIFICATE-----
"""


class TestValidation(TestCase):

    def test_valid(self):
        ca = Certificate(CA)
        certificate = Certificate(VALID)

        # test
        valid = certificate.verify([ca])

        # validation
        self.assertTrue(valid)

    def test_invalid(self):
        ca = Certificate(CA)
        certificate = Certificate(INVALID)

        # test
        valid = certificate.verify([ca])

        # validation
        self.assertFalse(valid)
