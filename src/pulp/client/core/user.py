#!/usr/bin/python
#
# Pulp Repo management module
#
# Copyright (c) 2010 Red Hat, Inc.

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
#

import os
import getpass
from gettext import gettext as _

from pulp.client import constants
from pulp.client.connection import UserConnection
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit
from pulp.client.credentials import CredentialError

# base user action class ------------------------------------------------------

class UserAction(Action):

    def setup_connections(self):
        try:
            self.userconn = UserConnection()
        except CredentialError, ce:
            system_exit(-1, str(ce))
        
    def get_user(self, username):
        user = self.userconn.user(login=username)
        if not user:
            system_exit(os.EX_DATAERR,
                        _("User [ %s ] does not exist") % username)
        return user


# user actions ----------------------------------------------------------------

class List(UserAction):

    description = _('list available users')

    def run(self):
        users = self.userconn.users()
        if not len(users):
            system_exit(os.EX_OK, _("No users available to list"))
        print_header(_('Available Users'))
        for user in users:
            print constants.AVAILABLE_USERS_LIST % (user["login"],
                                                    user["name"],
                                                    ', '.join(r for r in user['roles']))


class Create(UserAction):

    description = _('create a user')

    def setup_parser(self):
        self.parser.add_option("--username", dest="username",
                               help=_("new username to create (required)"))
        self.parser.add_option("--name", dest="name", default=None,
                               help=_("name of user for display purposes"))

    def run(self):
        newusername = self.get_required_option('username')
        while True:
            newpassword = getpass.getpass("Enter password for user %s: " % newusername)
            newpassword_confirm = getpass.getpass("Re-enter password for user %s: " % newusername)
            if newpassword == "" or newpassword_confirm == "":
                print _("\nUser password cannot be empty\n")
            elif newpassword == newpassword_confirm:
                break
            else:
                print _("\nPasswords do not match\n")
        name = self.opts.name
        user = self.userconn.create(newusername, newpassword, name)
        print _("Successfully created user [ %s ] with name [ %s ]") % \
                (user['login'], user['name'])


class Update(UserAction):

    description = _('update a user')

    def setup_parser(self):
        self.parser.add_option("--username", dest="username",
                               help=_("username of user you wish to edit. Not editable (required)"))
        self.parser.add_option("-P", "--password", dest="password", action='store_true', default=False,
                               help=_('change user password'))
        self.parser.add_option("--name", dest="name", default=None,
                               help=_("updated name of user for display purposes"))

    def run(self):
        username = self.get_required_option('username')
        name = self.opts.name

        user = self.get_user(username)
        if name is not None:
            user['name'] = name
        if self.opts.password:
            while True:
                newpassword = getpass.getpass("Enter new password for user %s: " % username)
                newpassword_confirm = getpass.getpass("Re-enter new password for user %s: " % username)
                if newpassword == "" or newpassword_confirm == "":
                    print _("\nUser password cannot be empty\n")
                elif newpassword == newpassword_confirm:
                    break
                else:
                    print _("\nPasswords do not match\n")
            user['password'] = newpassword
        self.userconn.update(user)
        print _("Successfully updated [ %s ] with name [ %s ]") % \
                (user['login'], user["name"])


class Delete(UserAction):

    description = _('delete a user')

    def setup_parser(self):
        self.parser.add_option("--username", dest="username",
                               help=_("username of user you wish to delete (required)"))

    def run(self):
        deleteusername = self.get_required_option('username')
        user = self.get_user(deleteusername)
        deleted = self.userconn.delete(login=deleteusername)
        if deleted:
            print _("Successfully deleted User [ %s ]") % deleteusername
        else:
            print _("User [%s] not deleted") % deleteusername

# user command ----------------------------------------------------------------

class User(Command):

    description = _('user specific actions to pulp server')
