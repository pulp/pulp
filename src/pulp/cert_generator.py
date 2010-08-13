from M2Crypto import X509, EVP, RSA, ASN1, util
import subprocess
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
    
    #Make a private key
    # Don't use M2Crypto directly as it leads to segfaults when trying to convert
    # the key to a PEM string.  Instead create the key with openssl and return the PEM string
    # Sorta hacky but necessary.
    # rsa = RSA.gen_key(1024, 65537, callback=passphrase_callback)
    private_key_pem = _make_priv_key()
    rsa = RSA.load_key_string(private_key_pem,
                              callback=util.no_passphrase_callback)
    
    # Make the Cert Request
    req, pub_key = _make_cert_request(uid, rsa)
    # Sign it with the Pulp server CA
    # We can't do this in m2crypto either so we have to shell out
    # TODO: We technically should be incrementing these serial numbers
    serial = "01"
    cmd = 'openssl x509 -req -sha1 -CA /etc/pki/pulp/ca.crt -CAkey /etc/pki/pulp/ca.key -set_serial %s -days 3650' % serial
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, 
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = p.communicate(input=req.as_pem())[0]
    p.wait()
    exit_code = p.returncode
    if (exit_code != 0):
        raise Exception("error signing cert request: %s" % output)
    cert_pem_string = output[output.index("-----BEGIN CERTIFICATE-----"):]
    return private_key_pem, cert_pem_string

def _make_priv_key():
    cmd = 'openssl genrsa 1024'
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    exit_code = p.returncode
    error = p.stderr.read()
    if (exit_code != 0):
        raise Exception("error generating private key: %s" % error)
    output = p.stdout.read()
    pem_str = output[output.index("-----BEGIN RSA PRIVATE KEY-----"):]
    return pem_str
    

def _make_cert_request(uid, rsa):
    pub_key = EVP.PKey()
    x = X509.Request()
    pub_key.assign_rsa(rsa)
    rsa = None # should not be freed here
    x.set_pubkey(pub_key)
    name = x.get_subject()
    name.CN = "%s" % uid
    ext2 = X509.new_extension('nsComment', 
        'Pulp Generated Identity Certificate for Consumer: [%s]' % uid)
    extstack = X509.X509_Extension_Stack()
    extstack.push(ext2)
    x.add_extensions(extstack)
    x.sign(pub_key,'sha1')
    pk2 = x.get_pubkey()
    return x, pub_key

