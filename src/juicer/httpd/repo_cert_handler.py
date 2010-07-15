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

import logging

from mod_python import apache

import juicer.httpd.repo_cert_validation as validation
import pulp.util

# Logging
format = logging.Formatter('%(asctime)s  %(message)s')
file_handler = logging.FileHandler('/var/log/pulp/repo_entitlement.log')
file_handler.setFormatter(format)
logging.getLogger('juicer').addHandler(file_handler)
logging.getLogger('juicer').setLevel(logging.DEBUG)

log = logging.getLogger(__name__)

# Pulp Configuration
config = pulp.util.Config(path='/etc/pulp/juicer.conf')

def authenhandler(req):
    # Needed to stuff the SSL variables into the request
    req.add_common_vars()

    # Only apply the entitlement certificate logic if juicer is configured to do so
    if config.repos.use_entitlement_certs.lower() == 'true':
        log.debug('Verifying client entitlement')
        cert_pem = req.ssl_var_lookup('SSL_CLIENT_CERT')

        if validation.is_valid(req.uri, cert_pem):
            req.user = 'foo'
            return apache.OK
        else:
            return apache.HTTP_UNAUTHORIZED
    else:
        req.user = 'foo'
        return apache.OK
