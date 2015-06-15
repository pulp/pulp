"""
Handles calls to the server that query the plugin and type capabilities.
"""

from pulp.bindings.base import PulpAPI


class ServerInfoAPI(PulpAPI):
    def __init__(self, pulp_connection):
        super(ServerInfoAPI, self).__init__(pulp_connection)
        self.base_path = 'v2/plugins/'

    def get_types(self):
        """
        Returns the list and descriptions of all content types installed on
        the server.

        @return: Response
        """
        path = self.base_path + 'types/'
        return self.server.GET(path)

    def get_importers(self):
        """
        Returns the list and descriptions of all importer types installed
        on the server.

        @return: Response
        """
        path = self.base_path + 'importers/'
        return self.server.GET(path)

    def get_distributors(self):
        """
        Returns the list and descriptions of all distributor types installed
        on the server.

        @return: Response
        """
        path = self.base_path + 'distributors/'
        return self.server.GET(path)


class ServerStatusAPI(PulpAPI):

    def get_status(self):
        """
        Returns the status of the server.

        :return: Response object
        :rtype:  pulp.bindings.responses.Response
        """
        path = 'v2/status/'
        return self.server.GET(path)
