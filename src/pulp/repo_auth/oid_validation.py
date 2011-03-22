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
Logic for checking a client certificate's OIDs to determine if a client
should have access to a resource.

The authenticate method is the logic driver. It performs the following functions:
  - Validates the client certificate against the CA certificate assigned to the repo
  - Looks for the download URL OIDs and verifies the requested URL matches at least
    one of them

The OID structure follows the Red Hat model. Download URLs are found at:
  1.3.6.1.4.1.2312.9.2.*.1.6

The * represents the product ID and is not used as part of this calculation.
'''

import re

import certificate


# -- framework -----------------------------------------------------------------

def authenticate(request, log_func):
    '''
    Framework hook method.
    '''
    cert_pem = request.ssl_var_lookup('SSL_CLIENT_CERT')

    # Check that the client has an entitlement for the requested URI. If not,
    # we can immediately fail the attempt.
    valid = _is_valid(request.uri, cert_pem)
    return valid

# -- private -------------------------------------------------------------------

def _is_valid(dest, cert_pem, log_func):
    '''
    Returns if the specified  certificate should be able to access a certain URL.

    @param dest: destination URL trying to be accessed
    @type  dest: string

    @param cert_pem: PEM encoded client certificate sent with the request
    @type  cert_pem: string
    '''

    cert = certificate.Certificate(content=cert_pem)
    extensions = cert.extensions()

    valid = False
    for e in extensions:
        if _is_download_url_ext(e):
            oid_url = extensions[e]

            if _validate(oid_url, dest):
                valid = True
                break

    if not valid:
        log_func('Request denied to destination [%s]' % dest)

    return valid

def _is_download_url_ext(ext_oid):
    '''
    Tests to see if the given OID corresponds to a download URL value.

    @param ext_oid: OID being tested; cannot be None
    @type  ext_oid: a certificiate.OID object

    @return: True if the OID contains download URL information; False otherwise
    @rtype:  boolean
    '''
    result = ext_oid.match('1.3.6.1.4.1.2312.9.2.') and ext_oid.match('.1.6')
    return result

def _validate(oid_url, dest):
    '''
    Returns whether or not the destination matches the OID download URL.

    @return: True if the OID permits the destination; False otherwise
    @rtype:  bool
    '''

    # Swap out all $ variables (e.g. $basearch, $version) for a reg ex wildcard in that location
    #
    # For example, the following entitlement:
    #   content/dist/rhel/server/$version/$basearch/os
    #
    # Should allow any value for the variables:
    #   content/dist/rhel/server/.+?/.+?/os
    
    oid_re = re.sub(r'\$.+?/', '.+?/', oid_url)

    return re.search(oid_re, dest) is not None
