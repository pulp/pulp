from gettext import gettext as _
from pkg_resources import get_distribution
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

from pulpcore.app.models.task import Worker
from pulpcore.app.serializers.status import StatusSerializer
from pulpcore.app.settings import INSTALLED_PULP_PLUGINS
from pulpcore.tasking.connection import get_redis_connection


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
        Returns app information including the version of pulpcore and loaded pulp plugins,
        known workers, database connection status, and messaging connection status
        """
        components = ['pulpcore'] + INSTALLED_PULP_PLUGINS
        versions = [{
            'component': component,
            'version': get_distribution(component).version
        } for component in components]
        redis_status = {'connected': self._get_redis_conn_status()}
        db_status = {'connected': self._get_db_conn_status()}

        try:
            online_workers = Worker.objects.online_workers()
        except Exception:
            online_workers = None

        try:
            missing_workers = Worker.objects.missing_workers()
        except Exception:
            missing_workers = None

        data = {
            'versions': versions,
            'online_workers': online_workers,
            'missing_workers': missing_workers,
            'database_connection': db_status,
            'redis_connection': redis_status
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
    def _get_redis_conn_status():
        """
        Returns True if pulp can connect to Redis

        Returns:
            bool: True if pulp can connect to Redis. False otherwise.
        """
        conn = get_redis_connection()
        try:
            conn.ping()
        except Exception:
            _logger.error(_('Connection to Redis failed during status check!'))
            return False
        else:
            return True
