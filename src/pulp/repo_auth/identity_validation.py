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
Logic for checking if a client certificate is an identity certificate.
Identity certificates are meant to be used by other Pulp components
to grant access without needing to care about specific entitlements.

The is_valid method is the logic driver. It performs the following functions:
  - Validates the client certificate against the CA certificate configured for Pulp
  - Ensures the CN of the certificate matches the identity string
'''

import certificate


IDENTITY_CN = 'pulp-identity'


# -- framework -----------------------------------------------------------------

def authenticate(request, log_func):
    '''
    Framework hook method.
    '''
    cert_pem = request.ssl_var_lookup('SSL_CLIENT_CERT')

    return _is_valid(cert_pem)

# -- private -------------------------------------------------------------------

def _is_valid(cert_pem):
    '''
    Returns if the specified  certificate should be able to access a certain URL.

    @param dest: destination URL trying to be accessed
    @type  dest: string

    @param cert_pem: PEM encoded client certificate sent with the request
    @type  cert_pem: string
    '''

    cert = certificate.Certificate(content=cert_pem)
    cn = cert.subject()['CN']

    return cn == IDENTITY_CN
