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

import threading
from types import NoneType

from pulp.server.db.model.auth import User
from pulp.server.util import Singleton

# thread-local principal storage -----------------------------------------------

_PRINCIPAL_STORAGE = threading.local()

# default system principal -----------------------------------------------------

_SYSTEM_ID = '00000000-0000-0000-0000-000000000000'
_SYSTEM_LOGIN = u'SYSTEM'


class SystemUser(User):
    """
    Singleton user class that represents the "system" user (i.e. no user).
    """

    __metaclass__ = Singleton

    def __init__(self):
        super(SystemUser, self).__init__(_SYSTEM_LOGIN, None)
        self._id = self.id = _SYSTEM_ID

# principal manager ------------------------------------------------------------

class PrincipalManager(object):
    """
    Manager that tracks the current user of the system.
    """

    # reference system attributes here for convenience
    system_id = _SYSTEM_ID
    system_login = _SYSTEM_LOGIN

    def get_principal(self):
        """
        Get the current user of the system,
        returning the default system user if there isn't one.
        @return: current user of the system
        @rtype: User or dict
        """
        return getattr(_PRINCIPAL_STORAGE, 'principal', SystemUser())

    def set_principal(self, principal=None):
        """
        Set the current user of the system to the provided principal,
        if no principal is provided, set the current user to the system user.
        @param principal: current user
        @type principal: User or None
        """
        _PRINCIPAL_STORAGE.principal = principal or SystemUser()

    def clear_principal(self):
        """
        Clear the current user of the system.
        """
        delattr(_PRINCIPAL_STORAGE, 'principal')

    def is_system_principal(self):
        """
        Determine if the current user is the default system user.
        @return: true if the current user is the system user, false otherwise
        @rtype: bool
        """
        return self.get_principal() is SystemUser()
