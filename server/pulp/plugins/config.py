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

        # May be set by the plugin in code to populate its defaults
        self.default_config = {}

    def keys(self):
        """
        Aggregates configuration keys across all three configuration sources
        and returns the list of them (duplicates are removed).

        @return: a single list representing all possible keys available
        @rtype:  list
        """
        keys = set()

        for c in self._all_configs():
            keys.update(c.keys())

        return list(keys)

    def get(self, key, default=None):
        """
        Returns the value for the given key searching through the possible
        configuration sources in the following order:
          1. override config
          2. repo config
          3. plugin config
          4. default config

        If the key is not found in any of the sources, the specified default
        value is returned. If there is no default provided, None is returned.

        @param key: configuration parameter to look up
        @type  key: str

        @param default: if the key is not present in any of the configuration
               sources, this value is returned
        @type  default: object

        @return: value for the configuration key
        """

        # Find the first config (ordered by priority) where the key is present
        for c in self._all_configs():
            if key in c:
                return c[key]

        return default

    def get_boolean(self, key):
        """
        Parses the given key as a boolean value. If the key is not present or
        is not one of the acceptable values for representing a boolean, None
        is returned.

        :param key: key to look up in the configuration
        :type  key: str

        :return: boolean representation of the value if it can be parsed; None otherwise
        :rtype:  bool, None
        """

        str_bool = self.get(key)

        # Handle the case where it's already a boolean
        if isinstance(str_bool, bool):
            return str_bool

        # If we're here, need to parse the string version of a boolean
        if str_bool is not None:
            str_bool = str_bool.lower()
            if str_bool == 'true':
                return True
            elif str_bool == 'false':
                return False
        return None

    def flatten(self):
        """
        Returns a single dict containing values aggregated across all sources after applying
        the priority rules. In other words, if a key is present in multiple sources, the highest
        priority value will be included in this dict.

        :rtype: dict
        """

        # Order matters so the highest priority value is used
        ordered_configs = (self.default_config, self.plugin_config,
                           self.repo_plugin_config, self.override_config)

        flattened = {}
        map(flattened.update, ordered_configs)
        return flattened

    def _all_configs(self):
        """
        Returns a single ordered list of all configurations to use in a lookup.
        The ordering in here defines the priority of the configurations and
        should not be changed.

        :return: list of configuration objects in this instance
        :rtype:  list
        """
        return (self.override_config, self.repo_plugin_config,
                self.plugin_config, self.default_config)
