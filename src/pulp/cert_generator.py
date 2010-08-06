from M2Crypto import X509, EVP, RSA, ASN1
import time
import socket
import logging

log = logging.getLogger(__name__)

def make_cert(uid):
    """
    Generate an x509 Certificate with the Subject set to
    the uid passed into this method:
    Subject: CN=someconsumer.example.com
    
    @param uid: ID of the Consumer you wish to embed in Certificate
    @return: X509 PEM Certificate string
    """
    # Ensure we are dealing with a string and not unicode
    uid = str(uid)
    log.debug("make_cert: [%s]" % uid)
    # Make the Cert Request
    req, pk = _make_cert_request(uid, 2048)
    
    # Now make the x509 Certificate
    pkey = req.get_pubkey()
    sub = req.get_subject()
    cert = X509.X509()
    cert.set_serial_number(1)
    cert.set_version(2)
    cert.set_subject(sub)
    t = long(time.time()) + time.timezone
    now = ASN1.ASN1_UTCTIME()
    now.set_time(t)
    nowPlusYear = ASN1.ASN1_UTCTIME()
    nowPlusYear.set_time(t + 60 * 60 * 24 * 365)
    cert.set_not_before(now)
    # Set to expire 1Y from now
    cert.set_not_after(nowPlusYear)
    issuer = X509.X509_Name()
    issuer.CN = socket.gethostname()
    issuer.O = 'Pulp Certificate Issuer.'
    cert.set_issuer(issuer)
    cert.set_pubkey(pkey)
    cert.set_pubkey(cert.get_pubkey()) # Make sure get/set work
    ext = X509.new_extension('subjectAltName', uid)
    ext.set_critical(0)
    cert.add_ext(ext)
    cert.sign(pk, 'sha1')
    assert cert.verify()
    assert cert.verify(pkey)
    assert cert.verify(cert.get_pubkey())
    return cert


def _make_cert_request(uid, bits):
    pk = EVP.PKey()
    x = X509.Request()
    rsa = RSA.gen_key(bits, 65537)
    pk.assign_rsa(rsa)
    rsa = None # should not be freed here
    x.set_pubkey(pk)
    name = x.get_subject()
    name.CN = "%s" % uid
    ext2 = X509.new_extension('nsComment', 
        'Pulp Generated Identity Certificate for Consumer: [%s]' % uid)
    extstack = X509.X509_Extension_Stack()
    extstack.push(ext2)
    x.add_extensions(extstack)
    x.sign(pk,'sha1')
    pk2 = x.get_pubkey()
    return x, pk

