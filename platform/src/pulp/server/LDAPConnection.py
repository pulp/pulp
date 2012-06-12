# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import ldap
import logging

import ldap.modlist

from pulp.server.config import config
from pulp.server.api.user import UserApi
from pulp.server.auth import authorization

_user_api = UserApi()
log = logging.getLogger(__name__)

class LDAPConnection:
    def __init__(self, admin=None, password=None,
                 server='ldap://localhost:389',
                 tls=False):
        self.ldapserver =  server
        self.ldapadmin  =  admin
        self.ldappassword = password
        self.ldaptls = tls
        self.lconn = None

    def connect(self):
        """
         Initialize connection to the ldap server
        """
        try:
            self.lconn = ldap.initialize(self.ldapserver)
        except ldap.LDAPError, err:
            log.error("Unable to establish a connection to LDAP server: %s" %
                      err)
            return False

        if self.ldaptls:
            try:
                self.lconn.start_tls_s()
            except ldap.LDAPError, err:
                if err[0]['info'] != 'TLS already started':
                    log.error("Could not start TLS: %s" % err)
                    return False

        try:
            if not self.ldapadmin or not self.ldappassword:
                # do an anonymous bind
                self.lconn.simple_bind_s()
            else:
                self.lconn.simple_bind_s(self.ldapadmin, self.ldappassword)
        except ldap.LDAPError, err:
            log.error("Unable to bind to LDAP server: %s" % err)
            return False
                

    def disconnect(self):
        """
         Disconnect from ldap server
        """
        self.lconn.unbind_s()

    def add_users(self, dn, attrs = {}):
        """
         @param dn: The dn of our new entry
                    ex: dn="cn=testuser,dc=example,dc=com"
         @param attrs: the "body" of the object
                    ex: attrs = {'objectclass' : ['top','organizationalRole'],
                                 'cn' : testuser,
                                 'sn' : testuser,
                                 'uid': testuser,
                                 'userPassword': xxyyzz,
                    }
        """
        ldif = ldap.modlist.addModlist(attrs)
        try:
            self.lconn.add_s(dn, ldif)
        except ldap.ALREADY_EXISTS:
            log.info('User %s already Exists on ldap server.' % dn)
        except ldap.LDAPError:
            log.error("Failed to add user with dn %s to the ldap server" % dn)

    def delete_users(self, dn):
        """
         @param dn: The dn of our entry to be deleted
                    ex: dn="cn=testuser,dc=example,dc=com"
        """
        try:
            self.lconn.delete_s(dn)
        except ldap.LDAPError, e:
            log.error("Failed to delete user with dn %s to the ldap server" % dn)
            
    def authenticate_user(self, base, username, password, filter=None):
        """
        @param base: The base DN of the ldap server
                     Ex: dc=example,dc=com
        @param username:  Userid to be validated in ldap server
        @param password: password credentials for userid
        @param filter: Optional additional LDAP filter to use when
                       searching for the user. Ex: (gidNumber=200)
        
        Returns the user info list with data in ldap server if the
        bind succeeds; else returns None
        """
        user = self.lookup_user(base, username, filter=filter)
        if user:
            userdn = user[0]
            try:
                self.lconn.simple_bind_s(userdn, password)
                log.info("Found user with id %s with matching credentials" %
                         username)
                return self._add_from_ldap(username, user)
            except:
                log.info("Invalid credentials for %s" % username)
                return None
        else:
            return None

    def _add_from_ldap(self, username, userdata):
        """
        @param username:  Username to be added
        @param user: tuple of user data as returned by lookup_user

        Adds a user to the pulp user database with no password and
        returns a pulp.server.db.model.User object
        """
        user = _user_api.user(username)
        if user is None:
            attrs = userdata[1]
            try:
                name = attrs['gecos']
            except KeyError:
                name = username
            user = _user_api.create(username, name=name)
            if config.has_option('ldap', 'default_role'):
                role = config.get('ldap', 'default_role')
                rv = authorization.add_user_to_role(role, username)
                if not rv:
                    log.error("Could not add user [%s] to role [%s]" %
                              (username, role))
                              
        return user

    def lookup_user(self, baseDN, user, filter=None):
        """
        @param baseDN: The base DN of the ldap server
                       ex: dc=example,dc=com
        @param user:   Userid to be validated in ldap server
        @param filter: Optional additional LDAP filter to use when
                       searching for the user. Ex: (gidNumber=200)

        If there is exactly one match, returns the user info list with
        data in ldap server.  Otherwise returns None
        """
        if filter:
            ldapfilter = "(&(uid=%s)%s)" % (user, filter)
        else:
            ldapfilter = "(uid=%s)" % user
        result = self.lconn.search_s(baseDN, ldap.SCOPE_SUBTREE, ldapfilter)
        if len(result) == 1:
            # exactly one result
            log.info("Found user with id %s" % user)
            return result[0]
        elif len(result) > 1:
            log.info("Found more than one match for id %s" % user)
        else:
            log.info("User %s Not Found." % user)
        return None

if __name__ == '__main__':
    ldapserv = LDAPConnection('cn=Directory Manager', \
                              'redhat',
                              'ldap://localhost')
    ldapserv.connect()
    print ldapserv.lookup_user("dc=rdu,dc=redhat,dc=com", "pulpuser1")
    print ldapserv.authenticate_user("dc=rdu,dc=redhat,dc=com", "pulpuser1", "redhat")
    ldapserv.disconnect()
