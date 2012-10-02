# Copyright (c) 2012 Red Hat, Inc.
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

SECTION_REMOVE = 'remove'
SECTION_UPLOADS = 'uploads'

SECTION_SYNC = 'sync'
SECTION_SYNC_SCHEDULES = 'schedules'
SECTION_PUBLISH = 'publish'
SECTION_PUBLISH_SCHEDULES = 'schedules'

DESC_ROOT = _('contains commands for working with Puppet repositories')
DESC_REPO = _('repository lifecycle commands')

DESC_REMOVE = _('remove copied or uploaded modules from a repository')
DESC_UPLOADS = _('upload modules into a repository')

DESC_SYNC = _('run, schedule, or view the status of sync tasks')
DESC_SYNC_SCHEDULES = _('manage repository sync schedules')
DESC_PUBLISH = _('run, schedule, or view the status of publish tasks')
DESC_PUBLISH_SCHEDULES = _('manage repository publish schedules')

# -- creation -----------------------------------------------------------------

def ensure_puppet_root(cli):
    """
    Verifies that the root of puppet-related commands exists in the CLI,
    creating it using constants from this module if it does not.

    :param cli: CLI instance being configured
    :type  cli: pulp.client.extensions.core.PulpCli
    """
    root_section = cli.find_section(SECTION_ROOT)
    if root_section is None:
        root_section = cli.create_section(SECTION_ROOT, DESC_ROOT)
    return root_section


def ensure_repo_structure(cli):
    """
    Verifies that the repository section and all of its subsections are present
    in the CLI, creating them using constants from this module if they are not.

    :param cli: CLI instance being configured
    :type  cli: pulp.client.extensions.core.PulpCli
    """

    # Make sure the puppet root is in place
    root_section = ensure_puppet_root(cli)

    # There's nothing dynamic about setting up the structure, so if the repo
    # section exists, it's a safe bet it's configured with its necessary
    # subsections, so just punch out.
    repo_section = root_section.find_subsection(SECTION_REPO)
    if repo_section is not None:
        return repo_section

    repo_section = root_section.create_subsection(SECTION_REPO, DESC_REPO)

    # Add the direct subsections of repo
    direct_subsections = (
        (SECTION_REMOVE, DESC_REMOVE),
        (SECTION_UPLOADS, DESC_UPLOADS),
        (SECTION_SYNC, DESC_SYNC),
        (SECTION_PUBLISH, DESC_PUBLISH),
    )
    for name, description in direct_subsections:
        repo_section.create_subsection(name, description)

    # Add specific third-tier sections
    sync_section = repo_sync_section(cli)
    sync_section.create_subsection(SECTION_SYNC_SCHEDULES, DESC_SYNC_SCHEDULES)

    publish_section = repo_publish_section(cli)
    publish_section.create_subsection(SECTION_PUBLISH_SCHEDULES, DESC_PUBLISH_SCHEDULES)

    return repo_section

# -- section retrieval --------------------------------------------------------

def repo_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO)


def repo_remove_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO, SECTION_REMOVE)


def repo_uploads_section(cli):
    return _find_section(cli, SECTION_ROOT, SECTION_REPO, SECTION_UPLOADS)


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

    :param cli: CLI instance to search within
    :type  cli: pulp.client.extensions.core.PulpCli
    :param path: path through the nest of sections to the desired section
    :type  path: list of str
    
    :return: section instance that matches the path
    :rtype:  pulp.client.extensions.core.PulpCliSection
    """
    section = cli.root_section
    for p in path:
        section = section.find_subsection(p)
    return section
