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

import threading

from pulp.server.util import Singleton

# default system principal ----------------------------------------------------

class SystemPrincipal(object):
    """
    Class representing the default "system" principal.
    """
    __metaclass__ = Singleton
    
    def __unicode__(self):
        return u'SYSTEM'
    
# thread-local storage for holding the current principal ----------------------

_storage = threading.local()

# principal api ---------------------------------------------------------------

def set_principal(principal):
    """
    Set the current principal (user) of the system.
    @param principal: current system user
    """
    _storage.principal = principal


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