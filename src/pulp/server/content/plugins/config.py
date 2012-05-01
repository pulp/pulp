# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
There are two locations plugin configuration can come from.
* Importer Configuration - the plugin-level configuration found in the config
  files provided for the plugin; this will be the same for all instances of
  the same plugin type
* Repository Configuration - the individual configuration of the plugin for a
  given repository; this is custom and used to dictate how the plugin should
  function when working with an individual repository

The Pulp server provides special handling for the repository configuration. Pulp
will track a static configuration for a plugin associated with a given repository.
This configuration is what is verified by the plugin through the
validate_config call.

For many calls, the Pulp server will allow users to override repo config values
for an individual call. These will not be persisted in the Pulp server and will
not be present for future calls (unless specified again by the user).

The classes in this module are used to simplify these configuration options into
a single API. Methods are provided for accessing values across all of the
different configuration types as well as accessing an individual configuration
area.
"""

class PluginCallConfiguration:
    """
    Provides APIs for retrieving values used to drive how a plugin should
    function for a given call on a repository.

    The lifespan of these instances is scoped to an individual call; the plugin
    should not cache these instances. It is possible that these instances
    contain one-off overridden configuration values that are not meant to
    persist between invocations on the plugin.
    """

    def __init__(self, plugin_config, repo_plugin_config, override_config=None):
        self.plugin_config = plugin_config or {}
        self.repo_plugin_config = repo_plugin_config or {}
        self.override_config = override_config or {}

    def keys(self):
        """
        Aggregates configuration keys across all three configuration sources
        and returns the list of them (duplicates are removed).

        @return: a single list representing all possible keys available
        @rtype:  list
        """
        keys = set()
        keys.update(self.plugin_config.keys())
        keys.update(self.repo_plugin_config.keys())
        keys.update(self.override_config.keys())
        return list(keys)

    def get(self, key, default=None):
        """
        Returns the value for the given key searching through the possible
        configuration sources in the following order:
          1. override config
          2. repo config
          3. plugin config

        If the key is not found in any of the sources, the specified default
        value is returned. If there is no default provided, None is returned.

        @param key: configuration parameter to look up
        @type  key: str

        @param default: if the key is not present in any of the configuration
               sources, this value is returned
        @type  default: object

        @return: value for the configuration key
        @rtype:  object
        """

        if key in self.override_config:
            return self.override_config[key]

        if key in self.repo_plugin_config:
            return self.repo_plugin_config[key]

        if key in self.plugin_config:
            return self.plugin_config[key]

        return default
