#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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

import base64
import logging
try:
    import json
except ImportError:
    import simplejson as json

import pymongo.json_util
import oauth2 as oauth 
import web

from ConfigParser import NoOptionError

import pulp.server.auth.auth as principal
from pulp.server import config
from pulp.server.api.user import UserApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.repo import RepoApi
from pulp.server.auth.certificate import Certificate
from pulp.server.auth import principal
import pulp.server.auth.password_util as password_util
import pulp.server.auth.cert_generator as cert_generator
from pulp.server.pexceptions import PulpException
from pulp.server.webservices import http
from pulp.server.LDAPConnection import LDAPConnection
from pulp.server.db.model import User

# globals ---------------------------------------------------------------------

LOG = logging.getLogger(__name__)
USER_API = UserApi()
CONSUMER_API = ConsumerApi()
REPO_API = RepoApi()

# decorator--------------------------------------------------------------------

class RoleCheck(object):
    '''
    Decorator class to check roles of web service caller.

    Copied and modified from:
      http://wiki.python.org/moin/PythonDecoratorLibrary#DifferentDecoratorForms
    '''

    def __init__(self, *dec_args, **dec_kw):
        '''The decorator arguments are passed here. Save them for runtime.'''
        self.dec_args = dec_args
        self.dec_kw = dec_kw

    def __call__(self, f):
        def check_roles(*fargs, **kw):
            '''
            Strip off the decorator arguments so we can use those to check the
            roles of the current caller.

            Note: the first argument cannot be "self" because we get a parse error
            "takes at least 1 argument" unless the instance is actually included in
            the argument list, which is redundant.  If this wraps a class instance,
            the "self" will be the first argument.
            '''

            # default the current principal to be sure it's not
            # left over from the last call.
            principal.clear_principal()
            
            
            for k in web.ctx.environ.keys():
                val = web.ctx.environ[k]
                LOG.error("env var: {%s:\'%s\'}" % (k, val))
                
            # Determine which roles will be checked by this instance of the decorator
            roles = {'consumer': None, 'admin': None, 'consumer_id': None}
            for key in self.dec_kw.keys():
                roles[key] = self.dec_kw[key]

            user = None
            # Admin role trumps any other checking
            if roles['admin']:
                # If not using cert check uname and password
                try:
                    user = self.check_admin(*fargs)
                    principal.set_principal(user)
                    LOG.info("User: %s" % user)
                except PulpException, pe:
                    http.status_unauthorized()
                    http.header('Content-Type', 'application/json')
                    return json.dumps(pe.value, default=pymongo.json_util.default)

            # Consumer role checking
            if not user and (roles['consumer'] or roles['consumer_id']):
                user = self.check_consumer(roles['consumer_id'], *fargs)
                
            # Last check for OAuth authentication
            if not user:
                user = self.check_oauth(*fargs)
                LOG.info("User from oauth check: %s" % user)
                
            # Check the Roles assigned to the User. Demo code
            # repo = REPO_API.repository(fargs[1])
            # LOG.error("REPO: %s" % repo)
            # LOG.error("User: %s" % user)
            # if (not ROLE_API.check(user, repo, RoleResourceType.REPO,
            #                               RoleActionType.READ)):
            #    LOG.error("Failed check!")
            #    user = None
            
            # Process the results of the auth checks
            if not user:
                http.status_unauthorized()
                http.header('Content-Type', 'application/json')
                return json.dumps("Authorization failed. Check your username and password or your certificate",
                                  default=pymongo.json_util.default)

            # If it wraps a class instance, call the function on the instance;
            # otherwise just call it directly
            if fargs and getattr(fargs[0], '__class__', None):
                instance, fargs = fargs[0], fargs[1:]
                result = f(instance, *fargs, **kw)

            else:
                result = f(*(fargs), **kw)

            return result

        # Save wrapped function reference
        self.f = f
        check_roles.__name__ = f.__name__
        check_roles.__dict__.update(f.__dict__)
        check_roles.__doc__ = f.__doc__
        return check_roles

    def check_admin(self, *fargs):
        '''
        Checks the request to see if it contains a valid admin authentication.

        @return: user instance of the authenticated user if valid
                 credentials were specified; None otherwise
        @rtype:  L{pulp.server.db.model.User}
        '''

        return self.check_admin_cert(*fargs) or self.check_username_pass(*fargs)




    def check_admin_cert(self, *fargs):
        '''
        Determines if the certificate in the request represents a valid admin certificate.

        @return: user instance of the authenticated user if valid
                 credentials were specified; None otherwise
        @rtype:  L{pulp.server.db.model.User}
        '''

        # Extract the certificate from the request
        environment = web.ctx.environ
        cert_pem = environment.get('SSL_CLIENT_CERT', None)

        # If there's no certificate, punch out early
        if cert_pem is None:
            return None

        # Parse the certificate and extract the consumer UUID
        idcert = Certificate(content=cert_pem)
        subject = idcert.subject()
        encoded_user = subject.get('CN', None)

        # On 11/17/10 (below) commented out.  Apache already doing this but left in
        # temporatily to reflect the change.  We should remove after this approach
        # proves out.

        # Verify the certificate has been signed by the pulp CA
        #valid = cert_generator.verify_cert(cert_pem)
        #if not valid:
        #    LOG.error('Admin certificate with CN [%s] is signed by a foreign CA' % encoded_user)
        #    return None

        # If there is no user/pass combo, this is not a valid admin certificate
        if not encoded_user:
            return None

        # Make sure the certificate is an admin certificate
        if not cert_generator.is_admin_user(encoded_user):
            return None

        # Parse out the username and id from the certificate information
        username, id = cert_generator.decode_admin_user(encoded_user)

        # Verify a user exists with the given name
        if config.config.has_section("ldap"):
            # found an ldap configuration, check to see if user exists
            user = self.check_user_pass_on_ldap(username)
        else:
            user = self.check_user_pass_on_pulp(username)
            # Verify the correct user ID
            if id != user['id']:
                LOG.error('ID in admin certificate for user [%s] was incorrect' % username)
                return None

        return user

    def check_oauth(self, *fargs):
        '''
        If the request uses OAuth HTTP authorization, verify the OAuth signature 
        and the pulp-user header to determine who the caller is 

        @return: user instance of the authenticated user if valid
                 credentials were specified; None otherwise
        @rtype:  L{pulp.server.db.model.User}
        '''
        # Get the credentials from the request
        user = None
        environment = web.ctx.environ
        auth_string = environment.get('HTTP_AUTHORIZATION', None)
        if not auth_string:
            return None
        
        scheme = environment.get('wsgi.url_scheme', None)
        host = environment.get('HTTP_HOST', None)
        uri = environment.get('REQUEST_URI', None)
        request_url = "%s://%s%s" % (scheme,host,uri)
        query_string = environment.get('QUERY_STRING', None)
        request_method = environment.get('REQUEST_METHOD', None)
        pulp_user =  environment.get('HTTP_PULP_USER', None)
        LOG.info("Pulp User      : %s" % pulp_user)
        headers = {"Authorization": auth_string}
        
        LOG.info("Request_method : %s" % request_method)
        LOG.info("request_url    : %s" % request_url)
        LOG.info("headers        : %s" % headers)
        LOG.info("query_string   : %s" % query_string)
        oauth_request = oauth.Request.from_request(request_method, request_url, 
                                       headers=headers, query_string=query_string)
        if oauth_request:
            try:
                key = config.config.get('security', 'oauth_key')
                secret = config.config.get('security', 'oauth_secret')
            except NoOptionError, noe:
                LOG.error(noe)
                LOG.error("Attempting OAuth authentication and you do not have oauth_key and oauth_secret in pulp.conf")
                return None
                
            consumer = oauth.Consumer(key=key, secret=secret)
            # token = oauth.Token(key, secret)
            # print "Token: %s" % token
            oauth_server = oauth.Server()
            oauth_server.add_signature_method(oauth.SignatureMethod_HMAC_SHA1())
            # If this passes then we have a valid oauth signature
            try:
                params = oauth_server.verify_request(oauth_request, consumer, None)
            except oauth.Error, e:
                LOG.error("error verifying OAuth signature : %s" % e)
                return None
            user = self._validate_user_exists(pulp_user)
            
        LOG.info("user from OAuth request: %s" % user)
        return user

    def check_username_pass(self, *fargs):
        '''
        If the request uses HTTP authorization, verify the credentials identify a
        valid user in the system.

        @return: user instance of the authenticated user if valid
                 credentials were specified; None otherwise
        @rtype:  L{pulp.server.db.model.User}
        '''

        # Get the credentials from the request
        environment = web.ctx.environ
        auth_string = environment.get('HTTP_AUTHORIZATION', None)

        # If credentials were passed in, verify them
        if auth_string is not None and auth_string.startswith("Basic"):

            # Parse out the credentials
            encoded_auth = auth_string.split(" ")[1]
            auth_string = base64.decodestring(encoded_auth)
            uname_pass = auth_string.split(":")
            username = uname_pass[0]
            password = uname_pass[1]

            # Verify a user exists with the given name
            if config.config.has_section("ldap"):
                # found an ldap configuration, check to see if user exists
                return self.check_user_pass_on_ldap(username, password)
            else:
                return self.check_user_pass_on_pulp(username, password)
        return None

    def check_user_pass_on_ldap(self, username, password=None):
        '''
        verify the credentials for user on ldap server.
        @param username: Userid to be validated on ldap server
        @param password: password credentials for userid
        @return: user instance of the authenticated user if valid
                 credentials were specified; None otherwise
        @rtype:  L{pulp.server.db.model.User}
        '''
        if not config.config.has_section("ldap"):
            LOG.info("No external ldap server available")
            return
        try:
            ldapserver = config.config.get("ldap", "uri")
        except:
            LOG.info("No valid server found, default to localhost")
            ldapserver = "ldap://localhost"
        try:
            base = config.config.get("ldap", "base")
        except:
            LOG.info("No valid base found, default to localhost")
            base = "dc=localhost"
        ldapserv = LDAPConnection(ldapserver)
        ldapserv.connect()
        if password:
            status = ldapserv.authenticate_user(base, username, password)
        else:
            status = ldapserv.lookup_user(base, username)

        LOG.info("User %s found in the ldap database: %s" % (username, status))
        ldapserv.disconnect()
        user = None
        if status:
            #create a transient user object to represent the ldap user
            user = User(username, username, password, username)
        return user

    def check_user_pass_on_pulp(self, username, password=None):
        '''
        verify the credentials for user on local pulp server.
        @param username: Userid to be validated on server
        @param password: password credentials for userid
        @return: user instance of the authenticated user if valid
                 credentials were specified; None otherwise
        @rtype:  L{pulp.server.db.model.User}
        '''
        user = self._validate_user_exists(username)
        if user is None:
            return None

        # Verify the correct password was specified
        if password:
            good_password = password_util.check_password(user['password'], password)
            if not good_password:
                LOG.error('Password for user [%s] was incorrect' % username)
                return None

        return user
    
    def _validate_user_exists(self, username):
        user = USER_API.user(username)
        if user is None:
            LOG.error('User [%s] specified in certificate was not found in the system' %
                      username)
            return None
        return user
            
    def check_consumer(self, check_id=False, *fargs):
        '''
        Determines if the certificate in the request represents a valid consumer certificate.

        @param check_id: if True, the consumer UID will be checked to make sure it
                         is present in the fargs argument; if False the only validation
                         will be that the UID exists in the DB (default = False)
        @type  check_id: boolean

        @return: user instance of the authenticated user if valid
                 credentials were specified; None otherwise
        @rtype:  L{pulp.server.db.model.User}
        '''

        # Extract the certificate from the request
        environment = web.ctx.environ
        cert_pem = environment.get('SSL_CLIENT_CERT', None)

        # If there's no certificate, punch out early
        if cert_pem is None:
            return None

        # Parse the certificate and extract the consumer UUID
        idcert = Certificate(content=cert_pem)
        subject = idcert.subject()
        consumer_cert_uid = subject.get('CN', None)

        # Verify the certificate has been signed by the pulp CA
        valid = cert_generator.verify_cert(cert_pem)
        if not valid:
            LOG.error('Consumer certificate with CN [%s] is signed by a foreign CA' % consumer_cert_uid)
            return None

        # If there is no consumer ID, this is not a valid consumer certificate
        if consumer_cert_uid is None:
            LOG.error("Consumer UID not found in certificate")
            return None

        # Check that it is a valid consumer in our DB
        consumer = CONSUMER_API.consumer(consumer_cert_uid)
        if not consumer:
            LOG.error("Consumer with id [%s] does not exist" % consumer_cert_uid)
            return None

        # If the ID should be explicitly verified against a provided list, the ID in the
        # certificate will be verified against the ID found in the certificate
        good_certificate = False
        if check_id:
            for arg in fargs:
                LOG.error("Checking ID in cert [%s] against expected ID [%s]" %
                          (consumer_cert_uid, arg))
                if arg == consumer_cert_uid:
                    good_certificate = True
                    break
        else:
            good_certificate = True

        if good_certificate:
            return consumer
        else:
            return None

