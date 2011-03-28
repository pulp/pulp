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
import protected_repo_utils
import repo_cert_utils


# -- constants -----------------------------------------------------------------

# This needs to be accessible on both Pulp and the CDS instances, so a
# separate config file for repo auth purposes is used.
CONFIG_FILENAME = '/etc/pulp/repo_auth.conf'

# This will run on both Pulp and CDS instances
PROTECTED_REPOS_FILENAME = '/etc/pki/content/pulp-protected-repos'

# This probably shouldn't be hardcoded. It's a config value in pulp.conf, but
# we can't read it from there in case this runs on a CDS. I'm also pretty sure
# Pulp would break in other ways if this was changed, so for now this is
# hardcoded until we actually get a use case to make it variable.
RELATIVE_URL = '/pulp/repos' # no trailing backslash since the relative paths will start with a /

# -- framework -----------------------------------------------------------------

def authenticate(request):
    '''
    Framework hook method.
    '''
    cert_pem = request.ssl_var_lookup('SSL_CLIENT_CERT')

    # Check that the client has an entitlement for the requested URI. If not,
    # we can immediately fail the attempt.
    valid = _is_valid(request.uri, cert_pem, request.log_error)
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

    # Load the repo credentials if they exist
    passes_individual_ca = False
    repo_bundle = _matching_repo_bundle(dest)
    if repo_bundle is not None:

        # If there is an individual bundle but no client certificate has been specified,
        # they are invalid
        if cert_pem == '':
            return False

        # Make sure the client cert is signed by the correct CA
        is_valid = repo_cert_utils.validate_certificate_pem(cert_pem, repo_bundle['ca'])
        if not is_valid:
            log_func('Client certificate did not match the repo consumer CA certificate')
            return False
        else:
            # Indicate it passed individual check so we don't run the global too
            passes_individual_ca = True

    # Load the global repo auth cert bundle and check it's CA against the client cert
    # if it didn't already pass the individual auth check
    global_bundle = repo_cert_utils.read_global_cert_bundle(['ca'])
    if not passes_individual_ca and global_bundle is not None:

        # If there is a global repo bundle but no client certificate has been specified,
        # they are invalid
        if cert_pem == '':
            return False

        # Make sure the client cert is signed by the correct CA
        is_valid = repo_cert_utils.validate_certificate_pem(cert_pem, global_bundle['ca'])
        if not is_valid:
            log_func('Client certificate did not match the global repo auth CA certificate')
            return False

    # If there were neither global nor repo auth credentials, auth passes.
    if global_bundle is None and repo_bundle is None:
        return True

    # If the credentials were specified for either case, apply the OID checks.
    is_valid = _check_extensions(cert_pem, dest, log_func)

    return is_valid

def _matching_repo_bundle(dest):

    # Load the path -> repo ID mappings
    prot_repos = protected_repo_utils.read_protected_repo_listings(PROTECTED_REPOS_FILENAME)

    # Extract the repo portion of the URL
    #   Example URL: https://guardian/pulp/repos/my-repo/pulp/fedora-13/i386/repodata/repomd.xml
    #   Repo Portion: /my-repo/pulp/fedora-13/i386/repodata/repomd.xml
    repo_url = dest[dest.find(RELATIVE_URL) + len(RELATIVE_URL):]

    # If the repo portion of the URL starts with any of the protected relative URLs,
    # it is considered to be a request against that protected repo
    repo_id = None
    for relative_url in prot_repos.keys():

        # I haven't found consistency in the relative URL setting on a repo, so make sure
        # it starts with a / to match what was ripped from the request URI
        test_pattern = relative_url
        if not test_pattern.startswith('/'):
            test_pattern = '/' + relative_url

        if repo_url.startswith(test_pattern):
            repo_id = prot_repos[relative_url]
            break

    if not repo_id:
        return None

    bundle = repo_cert_utils.read_consumer_cert_bundle(repo_id, ['ca'])
    return bundle

def _check_extensions(cert_pem, dest, log_func):

    cert = certificate.Certificate(content=cert_pem)
    extensions = cert.extensions()

    valid = False
    for e in extensions:
        if _is_download_url_ext(e):
            oid_url = extensions[e]

            if _validate_url(oid_url, dest):
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

def _validate_url(oid_url, dest):
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
