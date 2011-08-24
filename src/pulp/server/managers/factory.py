# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Provides a loosely coupled way of retrieving references into other manager
instances. Test cases can manipulate this module to mock out the class of
manager returned for a given type to isolate and simulate edge cases such
as exceptions.

When changing manager class mappings for a test, be sure to call reset()
in the test clean up to restore the mappings to the defaults. Failing to
do so may indirectly break other tests.
"""

import copy

from repo import RepoManager

# -- constants ----------------------------------------------------------------

# Keys used to look up a specific manager
TYPE_REPO    = 'repo-manager'
TYPE_CONTENT = 'content-manager'
TYPE_CDS     = 'cds-manager'

# Defaults for a normal running Pulp server (used to reset the state of the
# factory between runs)
_DEFAULTS = {
    TYPE_REPO : RepoManager,
}

# Mapping of key to class that will be instantiated in the factory method
# Initialized to a copy of the defaults so changes won't break the defaults
_CLASSES = copy.copy(_DEFAULTS)

# -- exceptions ---------------------------------------------------------------

class InvalidType(Exception):
    """
    Raised when a manager type is requested that has no class mapping.
    """

    def __init__(self, type_key):
        Exception.__init__(self)
        self.type_key = type_key

    def __str__(self):
        return 'Invalid manager type requested [%s]' % self.type_key

# -- public api ---------------------------------------------------------------

def get_manager(type_key):
    """
    Returns a manager instance of the given type according to the current
    manager class mappings.

    @param type_key: identifies the manager being requested; should be one of
                     the TYPE_* constants in this module
    @type  type_key: str

    @return: manager instance that (should) adhere to the expected API for
             managers of the requested type
    @rtype:  some sort of object  :)

    @raises InvalidType: if there is no class mapping for the requested type
    """

    if type_key not in _CLASSES:
        raise InvalidType(type_key)

    cls = _CLASSES[type_key]
    manager = cls()

    return manager

def register_manager(type_key, manager_class):
    """
    Sets the manager class for the given type key, either replacing the existing
    mapping or creating a new one.

    @param type_key: identifies the manager type
    @type  type_key: str

    @param manager_class: class to instantiate when requesting a manager of the
                          type specified in type_key
    @type  manager_class: class
    """

    _CLASSES[type_key] = manager_class

def reset():
    """
    Resets the type to class mappings back to the defaults. This should be called
    in test cleanup to prepare the state for other test runs.
    """

    global _CLASSES
    _CLASSES = copy.copy(_DEFAULTS)