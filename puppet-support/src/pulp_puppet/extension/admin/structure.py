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

"""
Contains methods related to the creation and navigation of the structure of the
Puppet branch of the CLI. This module should be used in place of the extensions
themselves creating or retrieving sections to centralize the organization of
the commands.
"""

from gettext import gettext as _

# -- constants ----------------------------------------------------------------

# Root section all puppet functionality will be located under
SECTION_ROOT = 'puppet'

SECTION_REPO = 'repo'

SECTION_GROUP = 'group'
SECTION_REMOVE = 'remove'
SECTION_UPLOADS = 'uploads'
SECTION_GROUP_MEMBERS = 'members'

SECTION_SYNC = 'sync'
SECTION_SYNC_SCHEDULES = 'schedules'
SECTION_PUBLISH = 'publish'
SECTION_PUBLISH_SCHEDULES = 'schedules'

DESCRIPTIONS = {
    SECTION_ROOT : _('contains commands for working with Puppet repositories'),
    SECTION_REPO : _('repository lifecycle commands'),

    SECTION_GROUP : _('repository group lifecycle commands'),
    SECTION_GROUP_MEMBERS : _('manage membership in a repository group'),
    SECTION_REMOVE : _('remove copied or uploaded modules from a repository'),
    SECTION_UPLOADS : _('upload modules into a repository'),

    SECTION_SYNC : _('run, schedule, or view the status of sync tasks'),
    SECTION_SYNC_SCHEDULES : _('manage repository sync schedules'),
    SECTION_PUBLISH : _('run, schedule, or view the status of publish tasks'),
    SECTION_PUBLISH_SCHEDULES : _('manage repository publish schedules'),
    }

# Relative to the root of the structure
STRUCTURE = {
    SECTION_REPO : {
        SECTION_GROUP : {
            SECTION_GROUP_MEMBERS: {},
        },
        SECTION_REMOVE : {},
        SECTION_UPLOADS : {},
        SECTION_SYNC : {
            SECTION_SYNC_SCHEDULES : {},
        },
        SECTION_PUBLISH : {
            SECTION_PUBLISH_SCHEDULES : {},
        }
    }
}

# -- creation -----------------------------------------------------------------

def ensure_structure(cli, root_section_name=SECTION_ROOT, structure=STRUCTURE,
                     descriptions=DESCRIPTIONS):
    """
    Ensures the proper section/subsection structure is in place in the CLI.
    This call is idempotent and is safe to call from all puppet-related extensions.

    :type cli: pulp.client.extensions.core.PulpCli
    """

    # If the section is already there, assume we've called this before and
    # punch out early.
    existing_root = cli.find_section(root_section_name)
    if existing_root:
        return

    # Create the necessary sections according to the structure definition
    def _create_subsection(parent, children_dict):
        for child_name, grandchildren in children_dict.items():
            child = parent.create_subsection(child_name, descriptions[child_name])
            _create_subsection(child, grandchildren)

    root = cli.create_section(root_section_name, descriptions[SECTION_ROOT])
    _create_subsection(root, structure)

# -- section retrieval --------------------------------------------------------

def repo_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO)

def repo_remove_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO, SECTION_REMOVE)

def repo_uploads_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO, SECTION_UPLOADS)

def repo_group_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO, SECTION_GROUP)

def repo_group_members_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO, SECTION_GROUP, SECTION_GROUP_MEMBERS)

def repo_sync_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO, SECTION_SYNC)

def repo_sync_schedules_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO, SECTION_SYNC, SECTION_SYNC_SCHEDULES)

def repo_publish_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO, SECTION_PUBLISH)

def repo_publish_schedules_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO, SECTION_PUBLISH, SECTION_PUBLISH_SCHEDULES)

# -- private ------------------------------------------------------------------

def _find_section(cli, *path):
    """
    Follows the given path to return the indicated section from the CLI.

    :type cli: pulp.client.extensions.core.PulpCli
    :param path: path through the nest of sections to the desired section
    :return: section instance that matches the path
    :rtype:  pulp.client.extensions.core.PulpCliSection
    """
    section = cli.root_section
    for p in path:
        section = section.find_subsection(p)
    return section
