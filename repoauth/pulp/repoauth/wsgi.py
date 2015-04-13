from pkg_resources import iter_entry_points

from pulp.repoauth import auth_enabled_validation

AUTH_ENTRY_POINT = 'pulp_content_authenticators'


def allow_access(environ, host):
    """
    Hook into mod_wsgi to be invoked when a request is determining authentication.
    If the authentication is successful, this method returns True. If
    validation fails, False is returned.

    :param environ: environ passed in from mod_wsgi
    :type  environ: dict of env vars

    :param host: hostname passed from mod_wsgi (not used)
    :type  host: str

    :return: True if the request is authorized or validation is disabled, otherwise False.
    :rtype:  Boolean
    """

    # If auth is disabled, then let the request continue. Note that this returns
    # True if auth is disabled.
    if auth_enabled_validation.authenticate(environ):
        return True

    # find all of the authenticator methods we need to try
    authenticators = {}
    for ep in iter_entry_points(group=AUTH_ENTRY_POINT):
        authenticators.update({ep.name: ep.load()})

    # loop through authenticators. If any return False, kick the user out.
    for auth_method in authenticators:
        if not authenticators[auth_method](environ):
            return False

    # if we get this far then the user is authorized
    return True
