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
Contains the manager class and exceptions for all repository related functionality.
"""

import sys
import logging

import pulp.plugins.loader as plugin_loader
import pulp.plugins.types.database as types_database
from pulp.server.exceptions import PulpExecutionException

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class PluginManager:

    def types(self):
        """
        Returns all type definitions loaded in the server. If no definitions
        are found, an empty list is returned.

        @return: list of type definitions
        @rtype:  list of dict
        """

        all_defs = types_database.all_type_definitions()
        return all_defs

    def importers(self):
        """
        Returns the names and versions of all importers loaded in the server.
        If no importers are found, an empty list is returned.

        @return: list of dicts containing metadata about the importer
        @rtype:  list
        """

        importer_dicts = plugin_loader.list_importers()
        result = []
        for i in importer_dicts:
            merged = importer_dicts[i]
            merged['id'] = i
            result.append(merged)
        return result

    def distributors(self):
        """
        Returns the names and versions of all distributors loaded in the server.
        If no distributors are found, an empty list is returned.

        @return: list of tuples indicating distributor name and version
        @rtype:  list of tuples (str, list of int)
        """

        distributor_dicts = plugin_loader.list_distributors()
        result = []
        for d in distributor_dicts:
            merged = distributor_dicts[d]
            merged['id'] = d
            result.append(merged)
        return result
    
    def profilers(self):
        """
        Returns the names and versions of all profilers loaded in the server.
        If no profilers are found, an empty list is returned.

        @return: list of tuples indicating profilers name and version
        @rtype:  list of tuples (str, list of int)
        """

        profiler_dicts = plugin_loader.list_profilers()
        result = []
        for d in profiler_dicts:
            merged = profiler_dicts[d]
            merged['id'] = d
            result.append(merged)
        return result


class PluginWrapper:
    """
    Plugin wrapper.
    Used to consistently wrap plugin method calls in a
    PulpExecutionException.
    """

    class Method:
        """
        Method wrapper.
        Used to consistently wrap plugin method calls in a
        PulpExecutionException.
        """

        def __init__(self, method):
            """
            @param method: method to be wrapped.
            @type method: instancemethod
            """
            self.__method = method

        def __call__(self, *args, **kwargs):
            try:
                return self.__method(*args, **kwargs)
            except Exception, e:
                msg = str(e)
                tb = sys.exc_info()[2]
                raise PulpExecutionException(msg), None, tb

    def __init__(self, plugin):
        """
        @param plugin: The plugin to be wrapped.
        @type plugin: Plugin
        """
        self.__plugin = plugin

    def __getattr__(self, name):
        attr = getattr(self.__plugin, name)
        if callable(attr):
            return self.Method(attr)
        else:
            return attr
