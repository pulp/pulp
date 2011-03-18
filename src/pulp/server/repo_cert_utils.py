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
 * 'key' - Private key for the certificate

The validate_cert_bundle method is used to ensure that only these keys are present
in a cert bundle dict.
'''

VALID_BUNDLE_KEYS = ['ca', 'cert', 'key']

def validate_cert_bundle(bundle):
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