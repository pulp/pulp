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
import sys
import traceback

from pulp.client.lib.logutil import getLogger 

log = getLogger(__name__)


class PluginLoader(object):

    plugin_base_class = object
    plugin_dirs = ["/usr/lib/pulp-plugins"]

    def __init__(self, cfg):
        self.cfg = cfg
        self.plugins = {}

    def get_plugin_dirs(self):
        if not self.cfg.plugins.plugin_dirs:
            return self.plugin_dirs
        else:
            return self.cfg.plugins.plugin_dirs.split('\n')

    def _load_plugins_from_file(self, file_name):
        # File name must end with .py or .pyc.
        if file_name.endswith(".py"):
            file_name = file_name[:-3]
        elif file_name.endswith(".pyc"):
            file_name = file_name[:-4]
        else:
            return

        # Replace path seperator with _ to get the module name.
        module_name = file_name.replace(os.path.sep, "_")

        # Try to import the module.
        try:
            module = __import__(module_name)
        except Exception, e:
            log.error("Could not import any plugins from %s. Import error "
                "was: '%s'" % (module_name, e))
            ei = sys.exc_info()
            log.debug(''.join(traceback.format_tb(ei[2])))
            return

        for name, mod_object in module.__dict__.items():
            try:
                if issubclass(mod_object, self.plugin_base_class):
                    # TODO: log info about laoding a plugin
                    plugin = mod_object(self.cfg)

                    if plugin.name in self.cfg._sections:
                        if "disabled" in self.cfg[plugin.name]._options:
                            if self.cfg[plugin.name].disabled.lower() == "true":
                                continue

                    self.plugins[name] = plugin
            except TypeError:
                continue

    def load_plugins(self):
        for plugin_dir in self.get_plugin_dirs():
            for root, dirs, files in os.walk(plugin_dir):
                sys.path.insert(0, root)
                for file_name in files:
                    self._load_plugins_from_file(file_name)
                sys.path.remove(root)

        return self.plugins
