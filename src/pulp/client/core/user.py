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
from gettext import gettext as _

from pulp.client import constants
from pulp.client.connection import setup_connection, UserConnection
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit

# base user action class ------------------------------------------------------

class UserAction(Action):

    def setup_connections(self):
        self.userconn = setup_connection(UserConnection)

# user actions ----------------------------------------------------------------

class List(UserAction):

    description = _('list available users')

    def run(self):
        users = self.userconn.users()
        if not len(users):
            system_exit(os.EX_OK, _("No users available to list"))
        print_header(_('Available Users'))
        for user in users:
            print constants.AVAILABLE_USERS_LIST % (user["login"], user["name"])


class Create(UserAction):

    description = _('create a user')

    def setup_parser(self):
        self.parser.add_option("--username", dest="username",
                               help=_("new username to create (required)"))
        self.parser.add_option("--password", dest="password", default='',
                               help=_("password for authentication"))
        self.parser.add_option("--name", dest="name", default='',
                               help=_("name of user for display purposes"))

    def run(self):
        newusername = self.get_required_option('username')
        newpassword = self.opts.password
        name = self.opts.name
        user = self.userconn.create(newusername, newpassword, name)
        print _("Successfully created user [ %s ] with name [ %s ]") % \
                (user['login'], user["name"])


class Delete(UserAction):

    description = _('delete a user')

    def setup_parser(self):
        self.parser.add_option("--username", dest="username",
                               help=_("username of user you wish to delete (required)"))

    def run(self):
        deleteusername = self.get_required_option('username')
        user = self.userconn.user(login=deleteusername)
        if not user:
            system_exit(os.EX_DATAERR,
                        _("User [ %s ] does not exist") % deleteusername)
        self.userconn.delete(login=deleteusername)
        print _("Successfully deleted User [ %s ]") % deleteusername

# user command ----------------------------------------------------------------

class User(Command):

    description = _('user specific actions to pulp server')
