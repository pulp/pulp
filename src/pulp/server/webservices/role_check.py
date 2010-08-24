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
import web

from pulp.server.api.user import UserApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.auth.certificate import Certificate
import pulp.server.auth.password_util as password_util
from pulp.server.pexceptions import PulpException
from pulp.server.webservices import http

log = logging.getLogger(__name__)

userApi = UserApi()
consumerApi = ConsumerApi()


class RoleCheck(object):
    '''decorator class to check Roles of caller.  Copied and modified from:
       
       http://wiki.python.org/moin/PythonDecoratorLibrary#DifferentDecoratorForms
    '''
    
    def __init__(self, *dec_args, **dec_kw):
        '''The decorator arguments are passed here.  Save them for runtime.'''
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
            
            # Determine which roles will be checked by this instance of the decorator
            roles = {'consumer': None, 'admin': None, 'consumer_id': None}
            for key in self.dec_kw.keys():
                roles[key] = self.dec_kw[key]
            
            admin_access_granted = False
            consumer_access_granted = False
            
            # Admin role trumps any other checking
            if roles['admin']:
                # If not using cert check uname and password
                try:
                    admin_access_granted = self.check_username_pass(*fargs)
                except PulpException, pe:
                    # TODO: Figure out how to re-use the same return function in base.py
                    http.status_unauthorized()
                    http.header('Content-Type', 'application/json')
                    return json.dumps(pe.value, default=pymongo.json_util.default)
            
            # Consumer role checking
            if not admin_access_granted and (roles['consumer'] or roles['consumer_id']):
                consumer_access_granted = self.check_consumer(roles['consumer_id'], *fargs)
                log.debug("consumer_access_granted? %s " % consumer_access_granted)

            # Process the results of the auth checks
            if not admin_access_granted and not consumer_access_granted:
                http.status_unauthorized()
                http.header('Content-Type', 'application/json')
                return json.dumps("Authorization Failure.  Check your username and password or your certificate", 
                                  default=pymongo.json_util.default)

            # If we get this far, access has been granted (in access failed the method
            # would have returned by now)

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

    def check_username_pass(self, *fargs):
        '''
        If the request uses HTTP authorization, verify the credentials identify a
        valid user in the system.

        @return: True if the user credentials are in the requests and are valid;
                 False otherwise
        @rtype:  boolean
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
            user = userApi.user(username)
            if (user is None):
                log.error("User [%s] specified in authentication was not found in the system" %
                          username)
                return False

            # Verify the correct password was specified
            good_password = password_util.check_password(user['password'], password)
            if not good_password:
                log.error('Password for user [%s] was incorrect' % username)

            return good_password

        return False
            
    def check_consumer(self, check_id=False, *fargs):
        '''
        Determines if the certificate in the request represents a valid consumer certificate.

        @param check_id: if True, the consumer UID will be checked to make sure it
                         is present in the fargs argument; if False the only validation
                         will be that the UID exists in the DB (default = False)
        @type  check_id: boolean

        @return: True if the request contains a valid certificate; False otherwise
        @rtype:  boolean
        '''

        # Extract the certificate from the request
        environment = web.ctx.environ
        cert_pem = environment.get('SSL_CLIENT_CERT', None)

        # If there's no certificate, punch out early
        if cert_pem is None:
            return False

        # Parse the certificate and extract the consumer UUID
        idcert = Certificate(content=cert_pem)
        subject = idcert.subject()
        consumer_cert_uid = subject.get('CN', None)

        # If there is no consumer ID, this is not a valid consumer certificate
        if consumer_cert_uid is None:
            log.error("Consumer UID not found in certificate")
            return False

        # Check that it is a valid consumer in our DB
        consumer = consumerApi.consumer(consumer_cert_uid)
        if not consumer:
            log.error("Consumer with id [%s] does not exist" % consumer_cert_uid)
            return False

        # If the ID should be explicitly verified against a provided list, the ID in the
        # certificate will be verified against the ID found in the certificate
        good_certificate = False
        if check_id:
            for arg in fargs:
                log.error("Checking ID in cert [%s] against expected ID [%s]" %
                          (consumer_cert_uid, arg))
                if arg == consumer_cert_uid:
                    good_certificate = True
                    break
        else:
            good_certificate = True

        return good_certificate
            
