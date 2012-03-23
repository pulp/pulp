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

    def unregistered(self):
        pass

    def bind(self, bind):
        """
        Apply a bind to the agent.
        @param bind: The bind added.
        @type bind: Bind
        """
        _LOG.info(bind)

    def unbind(self, bind):
        """
        Apply a unbind to the agent.
        @param bind: The bind removed.
        @type bind: Bind
        """
        _LOG.info(bind)

    def install_content(self, units, options):
        """
        Install content on a consumer.
        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Install options; based on unit type.
        @type options: dict
        """
        _LOG.info('units:%s, options:%s', units, options)

    def update_content(self, units, options):
        """
        Update content on a consumer.
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        """
        _LOG.info('units:%s, options:%s', units, options)

    def uninstall_content(self, units, options):
        """
        Uninstall content on a consumer.
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        """
        _LOG.info('units:%s, options:%s', units, options)


class BindCollection:
    """
    Normalized collection of bind/unbind.
    When iterated, renders a list of tuples of:
    (consumer_id, [repo_id,..])
    Used to effectiently perform bind/unbind on the
    consumer agent.
    """
    
    def __init__(self, binds):
        self.binds = binds
    
    def __iter__(self):
        consumers = {}
        for bind in self.binds:
            cid = bind['consumer_id']
            rid = bind['repo_id']
            repos = consumers.get(cid)
            if repos is None:
                repos = set()
                consumers[cid] = repos
            repos.add(rid)
        return iter(consumers.items())
