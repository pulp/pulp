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

import threading

from pulp.server.util import Singleton
from pulp.server.db.model import User

# default system principal ----------------------------------------------------

class SystemPrincipal(User):
    """
    Class representing the default "system" principal.
    """
    __metaclass__ = Singleton
    ID = '00000000-0000-0000-0000-000000000000'
    LOGIN = u'SYSTEM'

    def __init__(self):
        User.__init__(self, self.LOGIN, self.ID, self.LOGIN, self.LOGIN)

    def __unicode__(self):
        return self.LOGIN

# thread-local storage for holding the current principal ----------------------

_storage = threading.local()

# principal api ---------------------------------------------------------------

def set_principal(principal):
    """
    Set the current principal (user) of the system.
    @param principal: current system user
    """
    if principal:
        _storage.principal = principal
    else:
        clear_principal()


def get_principal():
    """
    Get the current principal (user) of the system.

    @return: current principal
    @rtype: pulp.server.db.model.User instance if one was specified in set_principal;
            pulp.server.auth.auth.SystemPrincipal otherwise
    """
    if not hasattr(_storage, 'principal'):
        _storage.principal = SystemPrincipal()
    return _storage.principal


def clear_principal():
    """
    Clear the current principal (user) of the system.
    This resets the principal to a "system" default.
    """
    _storage.principal = SystemPrincipal()


def is_system_principal():
    '''
    Returns True if the current principal is the system principal; False otherwise.
    '''
    return get_principal() is SystemPrincipal()
