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


import copy
import os
import sys
import traceback

from pulp.client.lib.logutil import getLogger 

log = getLogger(__name__)


class PluginLoader(object):
    """
    Plugin loader class.  Loads plugins from a set of plugin directories by
    importing each python module in those directories and checking to see if
    there are subclasses of C{PLUGIN_BASE_CLASS}.

    @cvar plugin_base_class: Class that plugins that should be discoverd by
    the loader should inherit from.
    @type plugin_base_class: class
    @cvar plugin_dirs: List of directories to search for loadable plugins.
    @type plugin_dirs: list
    """

    plugin_base_class = object
    plugin_dirs = []

    def __init__(self, cfg):
        self.cfg = cfg
        self.plugins = {}

    def get_plugin_dirs(self):
        """
        @return: List of directories to look for plugins.
        @rtype: list
        """
        if ("plugins" not in self.cfg._sections or 
           "plugin_dirs" not in self.cfg.plugins._options):
                return self.plugin_dirs
        else:
            return self.cfg.plugins.plugin_dirs.split('\n')

    def _load_plugins_from_file(self, file_name):
        """
        Load all plugins from C{file_name}.
        @param file_name: Name of file to intropsect for plugins.
        @type file_name: str
        """
        # File name must end with .py or .pyc.
        if file_name.endswith(".py"):
            file_name = file_name[:-3]
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

        # For each module level attribute, check if it is a sublcass of
        # self.plugin_base_class, if so, it's a plugin.
        for name, mod_object in module.__dict__.items():
            try:
                if issubclass(mod_object, self.plugin_base_class):
                    # Instantiate the plugin.
                    # TODO: use a copy of self.cfg, however iniparse on python
                    # 2.6 does not support deepcopy, so we need to come up
                    # with a different solution.
                    plugin = mod_object(self.cfg)

                    # Check for plugin disablement.  The disabled config
                    # value, if set, needs to be in the config section that
                    # matches the plugin name.
                    if plugin.name in plugin.cfg._sections:
                        if "enabled" in plugin.cfg[plugin.name]._options:
                            if plugin.cfg[plugin.name].enabled.lower() == "false":
                                continue

                    self.plugins[name] = plugin
            except TypeError:
                # issubclass throws TypeError if the 1st arg is not a class,
                # we can ignore this exception.
                continue

    def load_plugins(self):
        """
        The main API for this class, load_plugins will load all plugins this
        loader should and return them.
        @return: Loaded plugins
        @rtype: dict, keys of plugin names, values of plugin instances
        """
        for plugin_dir in self.get_plugin_dirs():
            for root, dirs, files in os.walk(plugin_dir):
                sys.path.insert(0, root)
                for file_name in files:
                    self._load_plugins_from_file(file_name)
                sys.path.remove(root)

        return self.plugins
