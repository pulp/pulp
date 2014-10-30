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

# -- constants ----------------------------------------------------------------

_NAMESPACE_DELIMITER = ':'
_PULP_NAMESPACE = 'pulp'
_ACTION_NAMESPACE = 'action'

RESOURCE_ANY_ID = "RESOURCE_ANY_ID"
RESOURCE_CDS_TYPE = 'cds'
RESOURCE_CONSUMER_TYPE = 'consumer'
RESOURCE_CONSUMER_BINDING_TYPE = 'consumer_binding'
RESOURCE_CONTENT_UNIT_TYPE = 'content_unit'
RESOURCE_REPOSITORY_TYPE = 'repository'
RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE = 'repository_distributor'
RESOURCE_REPOSITORY_IMPORTER_TYPE = 'repository_importer'
RESOURCE_REPOSITORY_GROUP_TYPE = 'repository_group'
RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE = 'repository_group_distributor'
RESOURCE_REPOSITORY_PROFILE_APPLICABILITY_TYPE = 'repository_profile_applicability'
RESOURCE_ROLE_TYPE = 'role'
RESOURCE_SCHEDULE_TYPE = 'schedule'
RESOURCE_USER_TYPE = 'user'
RESOURCE_CONTENT_SOURCE = 'content_source'


ACTION_SYNC_TYPE = 'sync'
ACTION_AUTO_PUBLISH_TYPE = 'auto_publish'
ACTION_PUBLISH_TYPE = 'publish'
ACTION_BIND = 'bind'
ACTION_AGENT_BIND = 'agent_bind'
ACTION_UNBIND = 'unbind'
ACTION_AGENT_UNBIND = 'agent_unbind'
ACTION_DELETE_BINDING = 'delete_binding'
ACTION_AGENT_UNIT_INSTALL = 'unit_install'
ACTION_AGENT_UNIT_UPDATE = 'unit_update'
ACTION_AGENT_UNIT_UNINSTALL = 'unit_uninstall'
ACTION_UPDATE_DISTRIBUTOR = 'update_distributor'
ACTION_REFRESH_CONTENT_SOURCE = 'refresh_content_source'
ACTION_REFRESH_ALL_CONTENT_SOURCES = 'refresh_all_content_sources'

# -- public -------------------------------------------------------------------

def action_tag(action_name):
    """
    Generate a pulp name-spaced tag for a given action.
    @param action_name: name of the action
    @type  action_name: basestring
    @return: tag
    @rtype:  str
    """
    return _NAMESPACE_DELIMITER.join((_PULP_NAMESPACE, _ACTION_NAMESPACE, action_name))

def is_action_tag(tag):
    """
    Indicates if a tag represents an action tag.
    @param tag: tag to test
    @type  tag: str
    @return: true if the tag is an action, false otherwise
    """
    indicator = _NAMESPACE_DELIMITER.join((_PULP_NAMESPACE, _ACTION_NAMESPACE))
    return tag.startswith(indicator)

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

def is_resource_tag(tag):
    """
    Indicates if a tag represents a resource tag.
    @param tag: tag to test
    @type  tag: str
    @return: true if the tag is a resource, false otherwise
    """
    # Ghetto implementation but it was the quickest; might be in trouble if we
    # add a third tag type.
    return not is_action_tag(tag)

def parse_value(tag):
    """
    Strips off the namespace information from the tag and returns its value.
    @param tag: tag to parse
    @type  tag: str
    @return: value of the tag
    @rtype:  str
    """
    pieces = tag.split(_NAMESPACE_DELIMITER, 2)
    return pieces[2]

def parse_resource_tag(tag):
    """
    Parses a resource tag, returning a tuple of resource type and ID.
    @param tag: tag to parse; must pass the is_resource_tag check
    @return: tuple of resource type to resource ID
    @rtype: (str, str)
    """
    if not is_resource_tag(tag):
        raise ValueError('Tag [%s] must be a valid resource tag' % tag)
    pieces = tag.split(_NAMESPACE_DELIMITER, 2)
    return pieces[1], pieces[2]
