# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os

from iniparse import INIConfig


class Plugin(object):
    """
    Base Plugin class for pulp client plugins.

    @cvar name: Plugin name used for identification purposes and to delineate
    the config section relevant to this plugin.
    @type name: str
    @cvar commands: List of Command classes that this plugin provides.
    @type commands: list
    @cvar CONFIG_FILE: Plugin config file name (optional).
    @type CONFIG_FILE: str
    """

    name = "plugin"

    commands = []

    CONFIG_FILE = None

    def __init__(self, cfg):
        """
        @param cfg: Main configuration of the pulp client.
        @type cfg: L{pulp.client.lib.config.Config}
        """

        self.cfg = cfg

        # Merge the plugin's config in with the main config.
        if self.CONFIG_FILE:
            config_path = os.path.join(self.cfg.BASE_PATH, self.CONFIG_FILE)
            self.cfg.merge(config_path)

        # Instantiate each command in self._commands
        self._commands = {}
        for command in self.commands:
            self._commands[command.name] = command(self.cfg)

    def __getattr__(self, attr):
        """
        Expose the plugin's commands as attributes on the instance.
        """
        return self.get_command(attr)

    def get_command(self, command_name):
        """
        Return the requested command.
        @param command_name: Command name.
        @type command_name: str
        @return: Instance of the requested command.
        @rtype: L{pulp.client.pluginlib.command.Command}
        """
        return self._commands[command_name]
