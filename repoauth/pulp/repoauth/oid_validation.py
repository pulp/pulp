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

from ConfigParser import NoOptionError, SafeConfigParser

from rhsm import certificate

from pulp.repoauth.protected_repo_utils import ProtectedRepoUtils
from pulp.repoauth.repo_cert_utils import RepoCertUtils

# This needs to be accessible on both Pulp and the CDS instances, so a
# separate config file for repo auth purposes is used.
CONFIG_FILENAME = '/etc/pulp/repo_auth.conf'


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
        self.repo_url_prefixes = self._get_repo_url_prefixes_from_config(config)

    def is_valid(self, dest, cert_pem, log_func):
        '''
        Returns if the specified  certificate should be able to access a certain URL.

        @param dest: destination URL trying to be accessed
        @type  dest: string

        @param cert_pem: PEM encoded client certificate sent with the request
        @type  cert_pem: string
        '''
        # Determine whether we should check the client certificates' signatures.
        try:
            verify_ssl = self.config.getboolean('main', 'verify_ssl')
        except NoOptionError:
            verify_ssl = True

        # Load the repo credentials if they exist
        repo_bundle = self._matching_repo_bundle(dest, self.repo_url_prefixes)
        # Load the global repo auth cert bundle and check it's CA against the client cert
        # if it didn't already pass the individual auth check
        global_bundle = self.repo_cert_utils.read_global_cert_bundle(log_func=log_func,
                                                                     pieces=['ca'])
        # If there were neither global nor repo auth credentials, auth passes.
        if global_bundle is None and repo_bundle is None:
            if self.repo_cert_utils.log_failed_cert_verbose:
                log_func('No global bundle or repo bundle found. Allowing request.')
            return True

        if verify_ssl:
            passes_individual_ca = False
            if repo_bundle is not None:

                # If there is an individual bundle but no client certificate has been specified,
                # they are invalid
                if cert_pem == '':
                    return False

                # Make sure the client cert is signed by the correct CA
                is_valid = self.repo_cert_utils.validate_certificate_pem(
                    cert_pem, repo_bundle['ca'], log_func=log_func)
                if not is_valid:
                    log_func('Client certificate did not match the repo consumer CA certificate')
                    return False
                else:
                    # Indicate it passed individual check so we don't run the global too
                    passes_individual_ca = True

            if not passes_individual_ca and global_bundle is not None:

                # If there is a global repo bundle but no client certificate has been specified,
                # they are invalid
                if cert_pem == '':
                    return False

                # Make sure the client cert is signed by the correct CA
                is_valid = self.repo_cert_utils.validate_certificate_pem(
                    cert_pem, global_bundle['ca'], log_func=log_func)
                if not is_valid:
                    log_func('Client certificate did not match the global repo auth CA certificate')
                    return False

        # If the credentials were specified for either case, apply the OID checks.
        is_valid = self._check_extensions(cert_pem, dest, log_func, self.repo_url_prefixes)
        if not is_valid:
            log_func("Client certificate failed extension check for destination: %s" % (dest))
        elif self.repo_cert_utils.log_failed_cert_verbose:
            log_func("OID validation successful for request")
        return is_valid

    def _matching_repo_bundle(self, dest, repo_url_prefixes):

        # Load the path -> repo ID mappings
        prot_repos = self.protected_repo_utils.read_protected_repo_listings()

        repo_id = None
        for prefix in repo_url_prefixes:
            # Extract the repo portion of the URL
            # Example: https://guardian/pulp/repos/my-repo/pulp/fedora-13/i386/repodata/repomd.xml
            #   Repo Portion: /my-repo/pulp/fedora-13/i386/repodata/repomd.xml
            repo_url = dest[dest.find(prefix) + len(prefix):]

            # If the repo portion of the URL starts with any of the protected relative URLs,
            # it is considered to be a request against that protected repo
            for relative_repo_url in prot_repos.keys():

                # Relative URL is inconsistent in Pulp, so a simple "startswith" tends to
                # break. Changing this to a find helps remove issues where the leading /
                # is missing, present, or duplicated.
                if repo_url.find(relative_repo_url) != -1:
                    repo_id = prot_repos[relative_repo_url]
                    break

            # break out of checking URLs once we find a matching repo id
            if repo_id:
                break

        # if we did not find a repo, return None
        if not repo_id:
            return None
        bundle = self.repo_cert_utils.read_consumer_cert_bundle(repo_id, ['ca'])
        return bundle

    def _check_extensions(self, cert_pem, dest, log_func, repo_url_prefixes):
        """
        Checks the requested destination path against the entitlement cert.

        :param cert_pem: certificate as PEM
        :type  cert_pem: str
        :param dest: path of desired destination
        :type  dest: str
        :param log_func: function used for logging
        :type  log_func: callable taking 1 argument of type basestring
        :param repo_url_prefixes: list of url prefixes to strip off before checking against cert
        :type  repo_url_prefixes: list of str
        :return: True iff request is authorized, else False
        :rtype:  bool
        """
        cert = certificate.create_from_pem(cert_pem)

        valid = False
        for prefix in repo_url_prefixes:
            # Extract the repo portion of the URL
            repo_dest = dest[dest.find(prefix) + len(prefix):]
            try:
                valid = cert.check_path(repo_dest)
            except AttributeError:
                # not an entitlement certificate, so no entitlements
                log_func('The provided client certificate is not an entitlement certificate.\n')
            # if we have a valid url check, no need to continue
            if valid:
                break

        if not valid:
            log_func('Request denied to destination [%s]' % dest)

        return valid

    def _get_repo_url_prefixes_from_config(self, config):
        """
        Obtain the list of repo URLs prefixes from the conf file. If none
        exist, just return "/pulp/repos" as the only entry.
        """
        try:
            prefixes = config.get('main', 'repo_url_prefixes').split(',')
        except NoOptionError:
            prefixes = ["/pulp/repos"]

        return prefixes
