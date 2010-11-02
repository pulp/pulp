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

import ldap
import logging

import ldap.modlist

log = logging.getLogger("LDAPConnection")

class LDAPConnection:
    def __init__(self, admin, password, server='ldap://localhost:389'):
        self.ldapserver =  server
        self.ldapadmin  =  admin
        self.ldappassword = password
        self.lconn = None

    def connect(self):
        """
         Initialize connection to the ldap server
        """
        try:
            self.lconn = ldap.initialize(self.ldapserver)
            self.lconn.simple_bind_s(self.ldapadmin, self.ldappassword)
        except ldap.LDAPError, e:
            log.error("Unable to establish a connection to ldap server")

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
            print self.lconn.add_s(dn, ldif)
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


    def lookup_user(self, baseDN, user, password=None):
        """
        @param baseDN: The base DN of the ldap server
                       ex: dc=example,dc=com
        @param user:  Userid to be validated in ldap server
        @param password: password credentials for userid

        Returns the user info list with data in ldap server
        """
        scope = ldap.SCOPE_SUBTREE
        if password:
            filter = "(|(uid=%s)(userPassword=%s))" % (user, password)
        else:
            filter = "(uid=%s)" % user
        result = self.lconn.search_s(baseDN, scope, filter)
        if result:
            log.info("Found user with id %s with matching credentials" % user)
        else:
            log.info("User %s Not Found.")
        return result


if __name__ == '__main__':
    ldapserv = LDAPConnection('cn=Directory Manager', \
                              'redhat',
                              'ldap://localhost:389')
    ldapserv.connect()
    ldapserv.lookup_user("dc=rdu,dc=redhat,dc=com", "pulpuser99", "redhat")
    ldapserv.disconnect()
