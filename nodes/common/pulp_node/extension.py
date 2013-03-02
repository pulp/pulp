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

from pulp.bindings.exceptions import NotFoundException

from pulp_node import constants


# --- constants --------------------------------------------------------------


SECTION_NAME = 'node'
SECTION_DESCRIPTION = _('pulp nodes related commands')


# --- utils ------------------------------------------------------------------

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


def node_activated(context, node_id):
    """
    Get whether a node has been activated.
    :param context: A client context.
    :type context: pulp.client.extensions.core.ClientContext
    :param node_id: The ID of the node being checked.
    :param node_id: str
    :return: True if activated.
    :rtype: bool
    """
    try:
        http = context.server.consumer.consumer(node_id)
        consumer = http.response_body
        notes = consumer['notes']
        return notes.get(constants.NODE_NOTE_KEY, False)
    except NotFoundException:
        return False


def repository_enabled(context, repo_id):
    """
    Get whether a repository is enabled.
    :param context: A client context.
    :type context: pulp.client.extensions.core.ClientContext
    :param repo_id: The ID of the repository being checked.
    :param repo_id: str
    :return: True if enabled.
    :rtype: bool
    """
    try:
        http = context.server.repo_distributor.distributors(repo_id)
        for dist in http.response_body:
            if dist['distributor_type_id'] in constants.ALL_DISTRIBUTORS:
                return True
        return False
    except NotFoundException:
        return False


def missing_resources(exception):
    """
    Generator use to get missing resources specified by an exception.
    :param exception: A NotFoundException exception.
    :type exception: pulp.bindings.exceptions.NotFoundException
    :return: generator of: (id, type)
    :rtype: tuple
    """
    for _type, _id in exception.extra_data['resources'].items():
        yield _id, _type