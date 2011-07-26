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

    name = "plugin"

    commands = []

    config_file = None

    def __init__(self, cfg):
        self.cfg = cfg
        if self.config_file:
            config_path = os.path.join(self.cfg.PATH, self.config_file)
            self.cfg.merge(config_path)

        self._commands = {}
        for command in self.commands:
            self._commands[command.name] = command(self.cfg)

    def get_command(self, command_name):
        return self._commands[command_name]
