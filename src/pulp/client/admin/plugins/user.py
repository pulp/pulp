#
# Pulp Repo management module
#
# Copyright (c) 2011 Red Hat, Inc.

# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import os
import getpass
from gettext import gettext as _

from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api.user import UserAPI
from pulp.client.lib.utils import print_header, system_exit
from pulp.client import constants
from pulp.client.pluginlib.command import Action, Command

# base user action class ------------------------------------------------------

class UserAction(Action):

    def __init__(self, cfg):
        super(UserAction, self).__init__(cfg)
        self.user_api = UserAPI()

    def get_user(self, username):
        user = self.user_api.user(login=username)
        if not user:
            system_exit(os.EX_DATAERR,
                        _("User [ %s ] does not exist") % username)
        return user

# user actions ----------------------------------------------------------------

class List(UserAction):

    name = "list"
    description = _('list available users')

    def run(self):
        users = self.user_api.users()
        if not len(users):
            system_exit(os.EX_OK, _("No users available to list"))
        print_header(_('Available Users'))
        for user in users:
            print constants.AVAILABLE_USERS_LIST % (user["login"],
                                                    user["name"],
                                                    ', '.join(r for r in user['roles']))


class Create(UserAction):

    name = "create"
    description = _('create a user')

    def setup_parser(self):
        self.parser.add_option("--username", dest="username",
                               help=_("new username to create (required)"))
        self.parser.add_option("--password", dest="password", default=None,
                               help=_("password for new user, if you do not want to be prompted for one"))
        self.parser.add_option("--ldap", dest="ldap", action="store_true",
                               default=False,
                               help=_("Create a passwordless local record for an LDAP user"))
        self.parser.add_option("--name", dest="name", default=None,
                               help=_("name of user for display purposes"))

    def run(self):
        newusername = self.get_required_option('username')
        if self.opts.password:
            newpassword = self.opts.password
        elif self.opts.ldap:
            newpassword = None
        else:
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
        user = self.user_api.create(newusername, newpassword, name)
        print _("Successfully created user [ %s ] with name [ %s ]") % \
                (user['login'], user['name'])


class Update(UserAction):

    name = "update"
    description = _('update a user')

    def setup_parser(self):
        self.parser.add_option("--username", dest="username",
                               help=_("username of user you wish to edit. Not editable (required)"))
        self.parser.add_option("--password", dest="password", default=None,
                               help=_("updated password for user; use -P if you do not wish to specify password on command line"))
        self.parser.add_option("-P", dest="passwd", action='store_true', default=False,
                               help=_("prompt for updated user password"))
        self.parser.add_option("--name", dest="name", default=None,
                               help=_("updated name of user for display purposes"))

    def run(self):
        username = self.get_required_option('username')
        user = self.user_api.user(username)
        if user is None:
            msg = _('No such user: %(u)s') % {'u': username}
            system_exit(os.EX_DATAERR, msg)
        delta = {}
        if self.opts.name:
            delta['name'] = self.opts.name
        if self.opts.password:
            delta['password'] = self.opts.password
        elif self.opts.passwd:
            while True:
                newpassword = getpass.getpass("Enter new password for user %s: " % username)
                newpassword_confirm = getpass.getpass("Re-enter new password for user %s: " % username)
                if newpassword == "" or newpassword_confirm == "":
                    print _("\nUser password cannot be empty\n")
                elif newpassword == newpassword_confirm:
                    break
                else:
                    print _("\nPasswords do not match\n")
            delta['password'] = newpassword
        self.user_api.update(username, delta)
        print _("Successfully updated [ %s ]" % username)


class Delete(UserAction):

    name = "delete"
    description = _('delete a user')

    def setup_parser(self):
        self.parser.add_option("--username", dest="username",
                               help=_("username of user you wish to delete (required)"))

    def run(self):
        deleteusername = self.get_required_option('username')
        user = self.get_user(deleteusername)
        deleted = self.user_api.delete(login=deleteusername)
        if deleted:
            print _("Successfully deleted User [ %s ]") % deleteusername
        else:
            print _("User [%s] not deleted") % deleteusername

# user command ----------------------------------------------------------------

class User(Command):

    name = "user"
    description = _('user specific actions to pulp server')

    actions = [ List,
                Create,
                Delete,
                Update ]

# user plugin ----------------------------------------------------------------

class UserPlugin(AdminPlugin):

    name = "user"
    commands = [ User ]
