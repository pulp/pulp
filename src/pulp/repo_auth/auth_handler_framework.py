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

from pulp.repo_auth import oid_validation, identity_validation, auth_enabled_validation

try:
    from mod_python import apache
except:
    # The import for apache fails when run outside of apache itself, such as in unit tests.
    # As annoying as this is, we still need to be able to test this class. So if it fails
    # to load, mock out our usage of it. Since the RPM required modpython to install, there
    # should be little risk of running into this scenario when actually running the code.

    class apache(object):
        HTTP_UNAUTHORIZED = 'unauthorized'
        OK = 'ok'
        APLOG_INFO = 'info'

# -- constants --------------------------------------------------------------------

REQUIRED_PLUGINS = ()

# The auth_enabled_validation runs first to prevent other plugins from running in
# case the config indicates repo auth should not be run
OPTIONAL_PLUGINS = (auth_enabled_validation.authenticate,
                    oid_validation.authenticate)

# -- modpython --------------------------------------------------------------------

def authenhandler(request):
    '''
    Hook into modpython to be invoked when a request is determining authentication.
    If the authentication is successful, this method populates the user inside of
    the request and returns an HTTP OK. If validation fails, the HTTP UNAUTHORIZED
    code is returned.

    @return: HTTP status code reflecting the result of authentication
    @rtype:  L{modpython.apache.OK} or L{modpython.apache.UNAUTHORIZED}
    '''
    code = _handle(request)

    # If the authentication was successful, we need to provide user information for apache,
    # since this handler will be configured as the authoritative source for user logins.
    # We don't actually need the user details anywhere else, so we can simply put anything
    # in the request's user value.
    if code == apache.OK:
        request.user = 'pulp_user'

    return code

# -- private -----------------------------------------------------------------------

def _handle(request):
    '''
    Performs the logic of authenticating the request against all registered plugins. The
    logic is as follows:

    - *All* required plugins must indicate that the authentication is valid
    - If any optional plugins are defined, *at least one* must indicate the authentication
      is valid

    Both of the above operations will short-circuit once the minimum requirements are met;
    there is no guarantee that every plugin will run on every request.

    @return: the coresponding HTTP access code (OK or UNAUTHORIZED) based on the results of
             the plugins and the above logic
    @rtype:  L{modpython.apache.OK} or L{modpython.apache.UNAUTHORIZED}
    '''

    # Needed to stuff the SSL variables into the request, do this now so all plugins
    # have access to this data
    request.add_common_vars()

    # First apply to the required handlers; if any of these fail we are immediately
    # unauthorized
    for f in REQUIRED_PLUGINS:
        result = f(request)

        if not result:
            request.log_error('Authorization failed by plugin [%s]' % f.__module__)
            return apache.HTTP_UNAUTHORIZED

    # If we get this far, the required plugins have passed. Run the optional plugins
    # and ensure that at least one of them passes.
    if len(OPTIONAL_PLUGINS) == 0:
        return apache.OK

    for f in OPTIONAL_PLUGINS:
        result = f(request)

        if result:
            return apache.OK

    return apache.HTTP_UNAUTHORIZED
