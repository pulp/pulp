'''
Logic for checking if the Pulp server is configured to apply *any* repo
authentication. This is meant to be used as a short-circuit validation
to prevent the more costly tests from being run in the case the Pulp server
doesn't care at all about repo authentication.
'''

from ConfigParser import SafeConfigParser

# This needs to be accessible on both Pulp and the CDS instances, so a
# separate config file for repo auth purposes is used.
CONFIG_FILENAME = '/etc/pulp/repo_auth.conf'


# -- framework------------------------------------------------------------------

def authenticate(environ):
    '''
    Framework hook method.
    '''
    config = _config()
    is_enabled = config.getboolean('main', 'enabled')
    is_verbose = config.getboolean('main', 'log_failed_cert_verbose')
    if not is_enabled and is_verbose:
        environ["wsgi.errors"].write("Repo authentication is not enabled. Skipping all checks.")

    # If auth is disabled, return true so the framework assumes a valid user has
    # been found and will short-circuit any other validation checks.
    return not is_enabled


def _config():
    config = SafeConfigParser()
    config.read(CONFIG_FILENAME)
    return config
