# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


_NAMESPACE_DELIMITER = ':'
_PULP_NAMESPACE = 'pulp'
_ACTION_NAMESPACE = 'action'


def action_tag(action_name):
    """
    Generate a pulp name-spaced tag for a given action.
    @param action_name: name of the action
    @type  action_name: basestring
    @return: tag
    @rtype:  str
    """
    return _NAMESPACE_DELIMITER.join((_PULP_NAMESPACE, _ACTION_NAMESPACE, action_name))

def resource_tag(resource_type, resource_id):
    """
    Generate a pulp name-spaced tag for a give resource.
    @param resource_type: the type of resource
    @type  resource_type: basestring
    @param resource_id: the resource's unique id
    @type  resource_id: basestring
    @return: tag
    @rtype:  str
    """
    return _NAMESPACE_DELIMITER.join((_PULP_NAMESPACE, resource_type, resource_id))
