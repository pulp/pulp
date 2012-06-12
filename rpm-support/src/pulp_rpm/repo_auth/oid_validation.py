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

from ConfigParser import SafeConfigParser
import re

from pulp_rpm.repo_auth import certificate
from pulp_rpm.repo_auth.protected_repo_utils import ProtectedRepoUtils
from pulp_rpm.repo_auth.repo_cert_utils import RepoCertUtils


# -- constants -----------------------------------------------------------------

# This needs to be accessible on both Pulp and the CDS instances, so a
# separate config file for repo auth purposes is used.
CONFIG_FILENAME = '/etc/pulp/repo_auth.conf'

# This probably shouldn't be hardcoded. It's a config value in pulp.conf, but
# we can't read it from there in case this runs on a CDS. I'm also pretty sure
# Pulp would break in other ways if this was changed, so for now this is
# hardcoded until we actually get a use case to make it variable.
RELATIVE_URL = '/pulp/repos' # no trailing backslash; we take care of normalizing it later

# -- framework -----------------------------------------------------------------

def authenticate(environ, config=None):
    '''
    Framework hook method.
    '''
    cert_pem = environ["mod_ssl.var_lookup"]("SSL_CLIENT_CERT")

    if config is None:
        config = _config()

    validator = OidValidator(config)
    valid = validator.is_valid(environ["REQUEST_URI"], cert_pem,
        environ["wsgi.errors"].write)
    return valid

def _config():
    config = SafeConfigParser()
    config.read(CONFIG_FILENAME)
    return config

class OidValidator:

    def __init__(self, config):
        self.config = config
        self.repo_cert_utils = RepoCertUtils(config)
        self.protected_repo_utils = ProtectedRepoUtils(config)

    def is_valid(self, dest, cert_pem, log_func):
        '''
        Returns if the specified  certificate should be able to access a certain URL.

        @param dest: destination URL trying to be accessed
        @type  dest: string

        @param cert_pem: PEM encoded client certificate sent with the request
        @type  cert_pem: string
        '''
        # Load the repo credentials if they exist
        passes_individual_ca = False
        repo_bundle = self._matching_repo_bundle(dest)
        if repo_bundle is not None:

            # If there is an individual bundle but no client certificate has been specified,
            # they are invalid
            if cert_pem == '':
                return False

            # Make sure the client cert is signed by the correct CA
            is_valid = self.repo_cert_utils.validate_certificate_pem(cert_pem, repo_bundle['ca'], log_func=log_func)
            if not is_valid:
                log_func('Client certificate did not match the repo consumer CA certificate')
                return False
            else:
                # Indicate it passed individual check so we don't run the global too
                passes_individual_ca = True

        # Load the global repo auth cert bundle and check it's CA against the client cert
        # if it didn't already pass the individual auth check
        global_bundle = self.repo_cert_utils.read_global_cert_bundle(['ca'])
        if not passes_individual_ca and global_bundle is not None:

            # If there is a global repo bundle but no client certificate has been specified,
            # they are invalid
            if cert_pem == '':
                return False

            # Make sure the client cert is signed by the correct CA
            is_valid = self.repo_cert_utils.validate_certificate_pem(cert_pem, global_bundle['ca'], log_func=log_func)
            if not is_valid:
                log_func('Client certificate did not match the global repo auth CA certificate')
                return False

        # If there were neither global nor repo auth credentials, auth passes.
        if global_bundle is None and repo_bundle is None:
            return True

        # If the credentials were specified for either case, apply the OID checks.
        is_valid = self._check_extensions(cert_pem, dest, log_func)
        if not is_valid:
            log_func("Client certificate failed extension check for destination: %s" % (dest))
        return is_valid

    def _matching_repo_bundle(self, dest):

        # Load the path -> repo ID mappings
        prot_repos = self.protected_repo_utils.read_protected_repo_listings()

        # Extract the repo portion of the URL
        #   Example URL: https://guardian/pulp/repos/my-repo/pulp/fedora-13/i386/repodata/repomd.xml
        #   Repo Portion: /my-repo/pulp/fedora-13/i386/repodata/repomd.xml
        repo_url = dest[dest.find(RELATIVE_URL) + len(RELATIVE_URL):]

        # If the repo portion of the URL starts with any of the protected relative URLs,
        # it is considered to be a request against that protected repo
        repo_id = None
        for relative_url in prot_repos.keys():

            # Relative URL is inconsistent in Pulp, so a simple "startswith" tends to
            # break. Changing this to a find helps remove issues where the leading /
            # is missing, present, or duplicated.
            if repo_url.find(relative_url) != -1:
                repo_id = prot_repos[relative_url]
                break

        if not repo_id:
            return None

        bundle = self.repo_cert_utils.read_consumer_cert_bundle(repo_id, ['ca'])
        return bundle

    def _check_extensions(self, cert_pem, dest, log_func):

        cert = certificate.Certificate(content=cert_pem)
        extensions = cert.extensions()

        # Extract the repo portion of the URL
        repo_dest = dest[dest.find(RELATIVE_URL) + len(RELATIVE_URL) + 1:]
        # Remove any initial or trailing slashes
        repo_dest = repo_dest.strip('/')

        valid = False
        for e in extensions:
            if self._is_download_url_ext(e):
                oid_url = extensions[e]

                if self._validate_url(oid_url, repo_dest):
                    valid = True
                    break

        if not valid:
            log_func('Request denied to destination [%s]' % dest)

        return valid

    def _is_download_url_ext(self, ext_oid):
        '''
        Tests to see if the given OID corresponds to a download URL value.

        @param ext_oid: OID being tested; cannot be None
        @type  ext_oid: a certificiate.OID object

        @return: True if the OID contains download URL information; False otherwise
        @rtype:  boolean
        '''
        result = ext_oid.match('1.3.6.1.4.1.2312.9.2.') and ext_oid.match('.1.6')
        return result

    def _validate_url(self, oid_url, dest):
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

        # Remove initial and trailing '/', and substitute the $variables for
        # equivalent regular expressions in oid_url.
        oid_re = re.sub(r'\$[^/]+(/|$)', '[^/]+/', oid_url.strip('/'))
        return re.match(oid_re, dest) is not None
