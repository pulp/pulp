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
from pulp.client.connection import UserConnection
from pulp.client.core.base import Action, Command, print_header, system_exit

# base user action class ------------------------------------------------------

class UserAction(Action):

    def connections(self):
        return {'userconn': UserConnection}

# user actions ----------------------------------------------------------------

class List(UserAction):

    name = 'list'
    description = 'list available users'

    def run(self):
        users = self.userconn.users()
        if not len(users):
            system_exit(os.EX_OK, _("no users available to list"))
        print_header(_('Available Users'))
        for user in users:
            print constants.AVAILABLE_USERS_LIST % (user["login"], user["name"])


class Create(UserAction):

    name = 'create'
    description = 'create a user'

    def setup_parser(self):
        self.parser.add_option("--username", dest="username",
                               help="new username to create")
        self.parser.add_option("--password", dest="password", default='',
                               help="password for authentication")
        self.parser.add_option("--name", dest="name", default='',
                               help="name of user for display purposes")

    def run(self):
        newusername = self.get_required_option('username')
        newpassword = self.opts.password
        name = self.opts.name
        user = self.userconn.create(newusername, newpassword, name)
        print _(" successfully created user [ %s ] with name [ %s ]") % \
                (user['login'], user["name"])


class Delete(UserAction):

    name = 'delete'
    description = 'delete a user'

    def setup_parser(self):
        self.parser.add_option("--username", dest="username",
                               help="username of user you wish to delete")

    def run(self):
        deleteusername = self.get_required_option('username')
        user = self.userconn.user(login=deleteusername)
        if not user:
            system_exit(os.EX_DATAERR,
                        _(" user [ %s ] does not exist") % deleteusername)
        self.userconn.delete(login=deleteusername)
        print _(" successfully deleted User [ %s ]") % deleteusername

# user command ----------------------------------------------------------------

class User(Command):

    name = 'user'
    description = _('user specific actions to pulp server')
    _default_actions = ('list', 'create', 'delete')

    def __init__(self, actions=None, action_state={}):
        super(User, self).__init__(actions, action_state)
        self.list = List()
        self.create = Create()
        self.delete = Delete()


command_class = User
