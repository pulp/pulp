"""
Contains the manager class and exceptions for all repository related functionality.
"""

from pulp.plugins.loader import api as plugin_api
import pulp.plugins.types.database as types_database


class PluginManager:

    def types(self):
        """
        Returns all type definitions loaded in the server. If no definitions
        are found, an empty list is returned.

        :return: list of type definitions
        :rtype:  list of dict
        """

        all_defs = types_database.all_type_definitions()
        return all_defs

    def importers(self):
        """
        Returns the names and versions of all importers loaded in the server.
        If no importers are found, an empty list is returned.

        :return: list of dicts containing metadata about the importer
        :rtype:  list
        """

        importer_dicts = plugin_api.list_importers()
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

        :return: list of tuples indicating distributor name and version
        :rtype:  list of tuples (str, list of int)
        """

        distributor_dicts = plugin_api.list_distributors()
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

        :return: list of tuples indicating profilers name and version
        :rtype:  list of tuples (str, list of int)
        """

        profiler_dicts = plugin_api.list_profilers()
        result = []
        for d in profiler_dicts:
            merged = profiler_dicts[d]
            merged['id'] = d
            result.append(merged)
        return result

    def catalogers(self):
        """
        Returns the names and versions of all catalogers loaded in the server.
        If no catalogers are found, an empty list is returned.

        :return: list of tuples indicating catalogers name and version
        :rtype:  list of tuples (str, list of int)
        """

        cataloger_dicts = plugin_api.list_catalogers()
        result = []
        for d in cataloger_dicts:
            merged = cataloger_dicts[d]
            merged['id'] = d
            result.append(merged)
        return result
