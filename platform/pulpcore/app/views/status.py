from gettext import gettext as _
from pkg_resources import get_distribution
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

from pulpcore.app.models.task import Worker
from pulpcore.app.serializers.status import StatusSerializer
from pulpcore.tasking.celery_instance import celery


_logger = logging.getLogger(__name__)


class StatusView(APIView):
    """
    Returns status information about the application
    """

    # allow anyone to access the status api
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):
        """
        Returns app information including the version, known workers, database connection status,
        and messaging connection status

        Args:
            request (rest_framework.request.Request): container representing request state
            format (str): requested format of the status response (e.g. json)

        Returns:
            rest_framework.response.Response: container for the response information
        """
        versions = [{'component': 'pulpcore', 'version': get_distribution("pulpcore").version}]
        broker_status = {'connected': self._get_broker_conn_status()}
        db_status = {'connected': self._get_db_conn_status()}

        try:
            workers = Worker.objects.all()
        except Exception:
            workers = None

        data = {
            'versions': versions,
            'known_workers': workers,
            'database_connection': db_status,
            'messaging_connection': broker_status
        }

        context = {'request': request}
        serializer = StatusSerializer(data, context=context)
        return Response(serializer.data)

    @staticmethod
    def _get_db_conn_status():
        """
        Returns True if pulp is connected to the database

        Returns:
            bool: True if there's a db connection. False otherwise.
        """
        try:
            Worker.objects.count()
        except Exception:
            _logger.exception(_('Cannot connect to database during status check.'))
            return False
        else:
            return True

    @staticmethod
    def _get_broker_conn_status():
        """
        Returns True if pulp can connect to the message broker

        Returns:
            bool: True if pulp can connect to the broker. False otherwise.
        """
        try:
            conn = celery.connection()
            conn.connect()
            conn.release()
        except Exception:
            _logger.exception(_('Connection to broker failed during status check!'))
            return False
        else:
            return True
