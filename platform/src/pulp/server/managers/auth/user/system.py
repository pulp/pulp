# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from pulp.server.db.model.auth import User
from pulp.server.util import Singleton


SYSTEM_ID = '00000000-0000-0000-0000-000000000000'
SYSTEM_LOGIN = u'SYSTEM'


class SystemUser(User):
    """
    Singleton user class that represents the "system" user (i.e. no user).
    """

    __metaclass__ = Singleton

    def __init__(self):
        super(SystemUser, self).__init__(SYSTEM_LOGIN, None)
        self._id = self.id = SYSTEM_ID


