'''
This module contains utilities to support operations around repo cert bundles
(both feed and consumer related). The functionality includes verifying a cert
bundle contains the required pieces, storage and retrieval, and managing the
distinction between feed and consumer bundles.

A cert bundle consists of three pieces:
 * Entitlement certificate that the caller specifies to the destination to
   present its credentials. This is an x509 certificate that is not necessarily
   unique to the consumer, but rather provides access to a repository.
 * Private key for the above x509 certificate.
 * Certificate Authority (CA) certificate. This varies depending on the type
   of cert bundle (feed v. consumer):
   * Feed: This is the CA used to sign the feed server's SSL certificate. It
     will be used to verify that the destination server is actually what Pulp
     expects it to be.
   * Consumer: This is the CA used to sign the entitlement certificate. This is
     used to verify the entitlement cert provided by the consumer wasn't forged.

In the above descriptions, the caller is the component requesting the repo data
(the Pulp server to the repo feed or the consumer) and the destination is the
component serving the data (the feed source or the Pulp server).

A cert bundle is represented by a dict with the following keys. The value at each key
is the PEM encoded contents of the certificate or key.
 * 'ca' - CA certificate
 * 'cert' - Certificate

The validate_cert_bundle method is used to ensure that only these keys are present
in a cert bundle dict.
'''

import logging
import shutil
import time
from threading import RLock
import os

from M2Crypto import X509, BIO
from pulp.common.util import encode_unicode
from pulp.server.common.openssl import Certificate


LOG = logging.getLogger(__name__)


# -- constants ----------------------------------------------------------------------------

VALID_BUNDLE_KEYS = ('ca', 'cert')
EMPTY_BUNDLE = dict([(key, None) for key in VALID_BUNDLE_KEYS])

# Single write lock for all repos and global; the usage should be infrequent enough
# that it's not an issue.
WRITE_LOCK = RLock()

GLOBAL_BUNDLE_PREFIX = 'pulp-global-repo'


class RepoCertUtils:
    def __init__(self, config):
        self.config = config
        self.log_failed_cert = True
        self.log_failed_cert_verbose = False
        self.max_num_certs_in_chain = 100
        try:
            self.log_failed_cert = self.config.getboolean('main', 'log_failed_cert')
        except:
            pass
        try:
            self.log_failed_cert_verbose = self.config.getboolean('main', 'log_failed_cert_verbose')
        except:
            pass
        try:
            self.max_num_certs_in_chain = self.config.getint('main', 'max_num_certs_in_chain')
        except:
            pass

    def delete_for_repo(self, repo_id):
        '''
        Deletes *all* cert bundles (feed and consumer) for the given repo. If no cert
        bundles have been stored for this repo, this method does nothing (will not
        throw an error).

        @param repo_id: identifies the repo
        @type  repo_id: str
        '''
        repo_dir = self._repo_cert_directory(repo_id)
        if type(repo_dir) is unicode:
            repo_dir = repo_dir.encode('utf8')
        if os.path.exists(repo_dir):
            LOG.info('Deleting certificate bundles at [%s]' % repo_dir)
            shutil.rmtree(repo_dir)

    def delete_global_cert_bundle(self):
        '''
        Deletes the global repo certificate bundle. If it does not exist, this call
        has no effect (no error is raised). This is meant as syntactic sugar for
        calling write_global_repo_cert_bundle with an empty bundle.
        '''
        self.write_global_repo_cert_bundle(None)

    # -- read calls ----------------------------------------------------------------

    def read_global_cert_bundle(self, log_func=None, pieces=VALID_BUNDLE_KEYS):
        '''
        Loads the contents of the global cert bundle. If pieces is specified, only
        the bundle pieces specified will be loaded (must be a subset of VALID_BUNDLE_KEYS).

        @param pieces: list of pieces of the bundle to load in this call; if unspecified,
                       all of the bundle components will be loaded
        @type  pieces: list of str

        @return: mapping of bundle piece to the contents of that bundle item (i.e. the
                 PEM encoded certificate, not a filename); returns None if the global
                 cert bundle does not exist
        @rtype:  dict {str, str} - keys will be taken from the pieces parameter; None
                 is returned if the global cert bundle does not exist
        '''

        cert_dir = self._global_cert_directory()

        result = None
        for suffix in pieces:
            filename = os.path.join(cert_dir, '%s.%s' % (GLOBAL_BUNDLE_PREFIX, suffix))

            if os.path.exists(filename):
                f = open(filename, 'r')
                contents = f.read()
                f.close()
                result = result or {}
                result[suffix] = contents
            elif self.log_failed_cert_verbose and log_func:
                log_func("Unable to find global cert [%s]" % filename)

        return result

    def global_cert_bundle_filenames(self, pieces=VALID_BUNDLE_KEYS):
        '''
        Returns the global cert bundle, but instead of the PEM encoded contents,
        a mapping of piece to its filename on disk is returned.

        @return: mapping of bundle piece to the filename where its contents can be found;
                 None if the repo is not configured for auth
        @rtype:  dict {str, str}
        '''

        cert_dir = self._global_cert_directory()

        result = None
        for suffix in pieces:
            filename = os.path.join(cert_dir, '%s.%s' % (GLOBAL_BUNDLE_PREFIX, suffix))
            if os.path.exists(filename):
                result = result or {}
                result[suffix] = filename

        return result

    def read_consumer_cert_bundle(self, repo_id, pieces=VALID_BUNDLE_KEYS):
        '''
        Loads the contents of a repo's consumer cert bundle. If pieces is specified, only
        the bundle pieces specified will be loaded (must be a subset of VALID_BUNDLE_KEYS).

        @param pieces: list of pieces of the bundle to load in this call; if unspecified,
                       all of the bundle components will be loaded
        @type  pieces: list of str

        @return: mapping of bundle piece to the contents of that bundle item (i.e. the
                 PEM encoded certificate, not a filename)
        @rtype:  dict {str, str} - keys will be taken from the pieces parameter; None
                 is returned if the a cert bundle does not exist for the repo
        '''

        cert_dir = self._repo_cert_directory(repo_id)

        result = None
        for suffix in pieces:
            filename = os.path.join(cert_dir, 'consumer-%s.%s' % (repo_id, suffix))

            if os.path.exists(filename):
                f = open(filename, 'r')
                contents = f.read()
                f.close()
                result = result or {}
                result[suffix] = contents

        return result

    def consumer_cert_bundle_filenames(self, repo_id, pieces=VALID_BUNDLE_KEYS):
        '''
        Returns a consumer cert bundle, but instead of the PEM encoded contents
        a mapping of piece to its filename on disk is returned.

        @return: mapping of bundle piece to the filename where its contents can be found;
                 None if the repo is not configured for auth
        @rtype:  dict {str, str}
        '''
        cert_dir = self._repo_cert_directory(repo_id)

        result = None
        for suffix in pieces:
            filename = os.path.join(cert_dir, 'consumer-%s.%s' % (repo_id, suffix))
            if os.path.exists(filename):
                result = result or {}
                result[suffix] = filename

        return result

    # -- write calls ----------------------------------------------------------------

    def write_feed_cert_bundle(self, repo_id, bundle):
        '''
        Writes the given feed cert bundle to disk. If bundle is None, any feed cert
        files that were previously written for this repo will be deleted.

        See _write_cert_bundle for details on params and return.
        '''
        cert_dir = self._repo_cert_directory(repo_id)
        return self._write_cert_bundle('feed-%s' % repo_id, cert_dir, bundle or EMPTY_BUNDLE)

    def write_consumer_cert_bundle(self, repo_id, bundle):
        '''
        Writes the given consumer cert bundle to disk. If bundle is None, any consumer cert
        files that were previously written for this repo will be deleted.

        See _write_cert_bundle for details on params and return.
        '''
        cert_dir = self._repo_cert_directory(repo_id)
        return self._write_cert_bundle('consumer-%s' % repo_id, cert_dir, bundle or EMPTY_BUNDLE)

    def write_global_repo_cert_bundle(self, bundle):
        '''
        Writes the given bundle to the global repo auth location. If bundle is None,
        any global repo auth files that were previously written for this repo will be deleted.

        See _write_cert_bundle for details on params and return.
        '''
        cert_dir = self._global_cert_directory()
        return self._write_cert_bundle(GLOBAL_BUNDLE_PREFIX, cert_dir, bundle or EMPTY_BUNDLE)

    # -- validate calls ----------------------------------------------------------------

    def validate_certificate(self, cert_filename, ca_filename):
        '''
        Validates a certificate against a CA certificate.
        Input expects filenames.

        @param cert_filename: full path to the PEM encoded certificate to validate
        @type  cert_filename: str

        @param ca_filename: full path to the PEM encoded CA certificate
        @type  ca_filename: str

        @return: true if the certificate was signed by the given CA; false otherwise
        @rtype:  boolean
        '''
        f = open(ca_filename)
        try:
            ca_data = f.read()
        finally:
            f.close()
        f = open(cert_filename)
        try:
            cert_data = f.read()
        finally:
            f.close()
        return self.validate_certificate_pem(cert_data, ca_data)

    def validate_certificate_pem(self, cert_pem, ca_pem, log_func=None):
        '''
        Validates a certificate against a CA certificate.
        Input expects PEM encoded strings.

        @param cert_pem: PEM encoded certificate
        @type  cert_pem: str

        @param ca_pem: PEM encoded CA certificates, allows chain of CA certificates if
        concatenated together
        @type  ca_pem: str

        @param log_func: a function to log debug messages
        @param log_func: a function accepting a single string

        @return: true if the certificate was signed by the given CA; false otherwise
        @rtype:  boolean
        '''
        if not log_func:
            log_func = LOG.info
        cert = X509.load_cert_string(cert_pem)
        ca_chain = self.get_certs_from_string(ca_pem, log_func)
        return self.x509_verify_cert(cert, ca_chain, log_func=log_func)

    def x509_verify_cert(self, cert, ca_certs, log_func=None):
        """
        Validates a Certificate against a CA Certificate.

        @param  cert:  Client certificate to verify
        @type   cert:  M2Crypto.X509.X509

        @param  ca_certs:  Chain of CA Certificates
        @type   ca_certs:  [M2Crypto.X509.X509]

        @param  log_func:  Logging function
        @param  log_func:  Function accepting a single string

        @return: true if the certificate is verified by OpenSSL APIs, false otherwise
        @rtype:  boolean
        """
        certificate = Certificate(cert.as_pem())
        ca_chain = [Certificate(c.as_pem()) for c in ca_certs]
        retval = certificate.verify(ca_chain)
        if retval != 1 and log_func:
            msg = "Cert verification failed against %d ca cert(s)" % len(ca_certs)
            if self.log_failed_cert:
                msg += "\n%s" % self.get_debug_info_certs(cert, ca_certs)
            log_func(msg)
        return retval

    def validate_cert_bundle(self, bundle):
        '''
        Validates that the given dict contains only the required pieces of a cert bundle.
        See the module level comments for more information on what contents are being
        checked. If the validation fails, an exception will be raised. If the bundle
        is valid, nothing is returned from this call.

        @param bundle: mapping of item to its PEM encoded contents; cannot be None
        @type  bundle: dict {str, str}

        @raises ValueError if the bundle is not a dict with the required keys
        '''
        if bundle is None:
            raise ValueError('Bundle must be specified')

        if type(bundle) != dict:
            raise ValueError('Bundle must be a dict; found [%s]' % type(bundle))

        missing_keys = [k for k in VALID_BUNDLE_KEYS if k not in bundle]
        if len(missing_keys) > 0:
            raise ValueError('Missing items in cert bundle [%s]' % ', '.join(missing_keys))

        extra_keys = [k for k in bundle.keys() if k not in VALID_BUNDLE_KEYS]
        if len(extra_keys) > 0:
            raise ValueError('Unexpected items in cert bundle [%s]' % ', '.join(extra_keys))

    def get_certs_from_string(self, data, log_func=None):
        """
        @param data: A single string of concatenated X509 Certificates in PEM format
        @type data: str

        @param log_func: logging function
        @type log_func: function accepting a single string

        @return list of X509 Certificates
        @rtype: [M2Crypto.X509.X509]
        """
        # Refer to OpenSSL crypto/x509/by_file.c
        # Function: X509_load_cert_file() to see how they parse a chain file and add
        # the certificates to a X509_Store.  Below follows a similar procedure.
        bio = BIO.MemoryBuffer(data)
        certs = []
        try:
            for index in range(0, self.max_num_certs_in_chain):
                # Read one cert at a time, 'bio' stores the last location read
                # Exception is raised when no more cert data is available
                cert = X509.load_cert_bio(bio)
                if not cert:
                    # This is likely to never occur, a X509Error should always be raised
                    break
                certs.append(cert)
                if index == (self.max_num_certs_in_chain - 1) and log_func:
                    log_func(
                        "**WARNING** Pulp reached maximum number of <%s> certs supported in a "
                        "chain." % self.max_num_certs_in_chain)

        except X509.X509Error:
            # This is the normal return path.
            return certs
        return certs

    def get_debug_info_certs(self, cert, ca_certs):
        """
        Debug method to display information certificates.  Typically used to print info after a
        verification failed.
        @param cert: a X509 certificate
        @type cert: M2Crypto.X509.X509

        @param ca_certs: list of X509 CA certificates
        @type ca_certs: [M2Crypto.X509.X509]

        @return: a debug message
        @rtype: str
        """
        msg = "Current Time: <%s>" % (time.asctime())
        if self.log_failed_cert_verbose:
            msg += "\n%s" % (cert.as_text())
        info = self.get_debug_X509(cert)
        msg += "\nCertificate to verify: \n\t%s" % (info)
        msg += "\nUsing a CA Chain with %s cert(s)" % (len(ca_certs))
        for ca in ca_certs:
            info = self.get_debug_X509(ca)
            msg += "\n\tCA: %s" % (info)
        return msg

    def get_debug_X509(self, cert):
        """
        @param cert: a X509 certificate
        @type cert: M2Crypto.X509.X509

        @return: string of debug information about the passed in X509
        @rtype: str
        """
        msg = "subject=<%s>, issuer=<%s>, subject.as_hash=<%s>, issuer.as_hash=<%s>, " \
              "fingerprint=<%s>, serial=<%s>, version=<%s>, check_ca=<%s>, notBefore=<%s>, " \
              "notAfter=<%s>" % \
              (cert.get_subject(), cert.get_issuer(), cert.get_subject().as_hash(),
               cert.get_issuer().as_hash(), cert.get_fingerprint(), cert.get_serial_number(),
               cert.get_version(), cert.check_ca(), cert.get_not_before(), cert.get_not_after())
        return msg

    def get_debug_X509_Extensions(self, cert):
        """
        @param cert: a X509 certificate
        @type cert: M2Crypto.X509.X509

        @return: debug string
        @rtype: str
        """
        extensions = ""
        ext_count = cert.get_ext_count()
        for i in range(0, ext_count):
            ext = cert.get_ext_at(i)
            extensions += " %s:<%s>" % (ext.get_name(), ext.get_value())
        return extensions

    # -- private ----------------------------------------------------------------------------

    def _write_cert_bundle(self, file_prefix, cert_dir, bundle):
        '''
        Writes the files represented by the cert bundle to a directory on the
        Pulp server unique to the given repo. If certificates already exist in the
        repo's certificate directory, they will be overwritten. If the value for
        any bundle component is None, the associated file will be erased if one
        exists. The file prefix will be used to differentiate between files that
        belong to the feed bundle v. those that belong to the consumer bundle.

        @param file_prefix: used in the filename of the bundle item to differentiate it
                            from other bundles; cannot be None
        @type  file_prefix: str

        @param cert_dir: absolute path to the location in which the cert bundle should
                         be written; cannot be None
        @type  cert_dir: str

        @param bundle: cert bundle (see module docs for more information on format)
        @type  bundle: dict {str, str}

        @raises ValueError: if bundle is invalid (see validate_cert_bundle)

        @return: mapping of cert bundle item (see module docs) to the absolute path
                 to where it is stored on disk
        '''
        file_prefix = encode_unicode(file_prefix)
        cert_dir = encode_unicode(cert_dir)

        WRITE_LOCK.acquire()

        try:
            # Create the cert directory if it doesn't exist
            if not os.path.exists(cert_dir):
                os.makedirs(cert_dir)

            # For each item in the cert bundle, save it to disk using the given prefix
            # to identify the type of bundle it belongs to. If the value is None, the
            # item is being deleted.
            cert_files = {}
            for key, value in bundle.items():
                filename = os.path.join(cert_dir, '%s.%s' % (file_prefix, key))

                try:

                    if value is None:
                        if os.path.exists(filename):
                            LOG.info('Removing repo cert file [%s]' % filename)
                            os.remove(filename)
                        cert_files[key] = None
                    else:
                        LOG.info('Storing repo cert file [%s]' % filename)
                        f = open(filename, 'w')
                        f.write(value)
                        f.close()
                        cert_files[key] = str(filename)
                except:
                    LOG.exception('Error storing certificate file [%s]' % filename)
                    raise Exception('Error storing certificate file [%s]' % filename)

            return cert_files

        finally:
            WRITE_LOCK.release()

    def _repo_cert_directory(self, repo_id):
        '''
        Returns the absolute path to the directory in which certificates for the
        given repo are stored.

        @return: absolute path to a directory that may not exist
        @rtype:  str
        '''
        cert_location = self.config.get('repos', 'cert_location')
        cert_dir = os.path.join(cert_location, repo_id)
        return cert_dir

    def _global_cert_directory(self):
        '''
        Returns the absolute path to the directory in which global repo auth
        credentials are stored.

        @return: absolute path to a directory that may not exist
        @rtype:  str
        '''
        global_cert_location = self.config.get('repos', 'global_cert_location')
        return global_cert_location
