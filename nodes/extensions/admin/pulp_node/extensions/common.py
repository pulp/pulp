# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _


# --- constants -------------------------------------------------------------------------


SECTION_NAME = _('node')
SECTION_DESCRIPTION = _('pulp nodes related commands')


# --- utils -----------------------------------------------------------------------------

def ensure_node_section(cli):
    """
    Ensures that the root section of node-related commands exists in the CLI,
    creating it using constants from this module if it does not.
    :param cli: CLI instance being configured
    :type cli: pulp.client.extensions.core.PulpCli
    """
    section = cli.find_section(SECTION_NAME)
    if section is None:
        section = cli.create_section(SECTION_NAME, SECTION_DESCRIPTION)
    return section
