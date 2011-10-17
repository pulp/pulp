#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

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
import subprocess
from threading import RLock
import os

from M2Crypto import X509


# -- constants ----------------------------------------------------------------------------

VALID_BUNDLE_KEYS = ('ca', 'cert')
EMPTY_BUNDLE = dict([(key, None) for key in VALID_BUNDLE_KEYS])

# Single write lock for all repos and global; the usage should be infrequent enough
# that it's not an issue.
WRITE_LOCK = RLock()

GLOBAL_BUNDLE_PREFIX = 'pulp-global-repo'

LOG = logging.getLogger(__name__)


class RepoCertUtils:

    def __init__(self, config):
        self.config = config

    # -- delete calls ----------------------------------------------------------------

    def delete_for_repo(self, repo_id):
        '''
        Deletes *all* cert bundles (feed and consumer) for the given repo. If no cert
        bundles have been stored for this repo, this method does nothing (will not
        throw an error).

        @param repo_id: identifies the repo
        @type  repo_id: str
        '''
        repo_dir = self._repo_cert_directory(repo_id)

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

    def read_global_cert_bundle(self, pieces=VALID_BUNDLE_KEYS):
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

        @param cert_filename: full path to the PEM encoded certificate to validate
        @type  cert_filename: str

        @param ca_filename: full path to the PEM encoded CA certificate
        @type  ca_filename: str

        @return: true if the certificate was signed by the given CA; false otherwise
        @rtype:  boolean
        '''

        ca = X509.load_cert(ca_filename)
        cert = X509.load_cert(cert_filename)
        return cert.verify(ca.get_pubkey())

    def validate_certificate_pem(self, cert_pem, ca_filename):
        '''
        Validates a certificate against a CA certificate.

        @param cert_pem: PEM encoded certificate
        @type  cert_pem: str

        @param ca_filename: full path to the PEM encoded CA certificate
        @type  ca_filename: str

        @return: true if the certificate was signed by the given CA; false otherwise
        @rtype:  boolean
        '''

        cmd = 'openssl verify -CAfile %s' % ca_filename
        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Use communicate to pipe the certificate to the verify call
        stdout, stderr = p.communicate(input=cert_pem)

        result = stdout.rstrip()

        # Successful result example:
        #   stdin: OK\n
        # Failed result example:
        #   stdin: C = US, ST = NC, L = Raleigh, O = Red Hat, CN = localhost
        #   error 20 at 0 depth lookup:unable to get local issuer certificate\n
        valid = result.endswith('OK')

        return valid

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
