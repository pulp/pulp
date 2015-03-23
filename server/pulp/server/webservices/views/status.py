"""
Unauthenticated status API so that other can make sure we're up (to no good).
"""

from django.views.generic import View

import pulp.server.managers.status as status_manager
from pulp.server.webservices.views.util import generate_json_response_with_pulp_encoder


class StatusView(View):
    """
    View for server status
    """

    def get(self, request):
        """
        Show current status of pulp server.

        :param request: WSGI request object
        :type request: django.core.handlers.wsgi.WSGIRequest

        :return: Response showing surrent server status
        :rtype: django.http.HttpResponse
        """
        pulp_version = status_manager.get_version()
        pulp_db_connection = status_manager.get_mongo_conn_status()
        pulp_messaging_connection = status_manager.get_broker_conn_status()

        # do not ask for the worker list unless we have a DB connection
        if pulp_db_connection['connected']:
            pulp_workers = [w for w in status_manager.get_workers()]
        else:
            pulp_workers = []

        # 'api_version' is deprecated and can go away in 3.0, bz #1171763
        status_data = {'api_version': '2',
                       'versions': pulp_version,
                       'database_connection': pulp_db_connection,
                       'messaging_connection': pulp_messaging_connection,
                       'known_workers': pulp_workers}

        return generate_json_response_with_pulp_encoder(status_data)
