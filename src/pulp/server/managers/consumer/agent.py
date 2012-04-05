#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
#
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
Contains agent management classes
"""

from logging import getLogger


_LOG = getLogger(__name__)


class AgentManager(object):
    """
    The agent manager.
    """

    def unregistered(self, id):
        """
        Notification that a consumer (agent) has
        been unregistered.  This ensure that all registration
        artifacts have been cleaned up.
        @param id: The consumer ID.
        @type id: str
        """
        _LOG.info(id)

    def bind(self, bind):
        """
        Apply a bind to the agent.
        @param bind: The bind added.
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>}
        @type bind: dict
        """
        _LOG.info(bind)

    def unbind(self, bind):
        """
        Apply a unbind to the agent.
        @param bind: The bind removed.
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>}
        @type bind: dict
        """
        _LOG.info(bind)

    def install_content(self, id, units, options):
        """
        Install content units on a consumer.
        @param id: The consumer ID.
        @type id: str
        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Install options; based on unit type.
        @type options: dict
        """
        _LOG.info('id:%s units:%s, options:%s', id, units, options)

    def update_content(self, id, units, options):
        """
        Update content units on a consumer.
        @param id: The consumer ID.
        @type id: str
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        """
        _LOG.info('id:%s units:%s, options:%s', id, units, options)

    def uninstall_content(self, id, units, options):
        """
        Uninstall content units on a consumer.
        @param id: The consumer ID.
        @type id: str
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        """
        _LOG.info('id:%s units:%s, options:%s', id, units, options)

    def send_profile(self, id):
        """
        Send the content profile(s).
        @param id: The consumer ID.
        @type id: str
        """
        _LOG.info(id)
