from gettext import gettext as _
from rest_framework import serializers

from pulpcore.app.serializers.task import WorkerSerializer


class VersionSerializer(serializers.Serializer):
    """
    Serializer for the version information of Pulp components
    """

    component = serializers.CharField(
        help_text=_("Name of a versioned component of Pulp"),
    )

    version = serializers.CharField(
        help_text=_("Version of the component (e.g. 3.0.0)"),
    )


class DatabaseConnectionSerializer(serializers.Serializer):
    """
    Serializer for the database connection information
    """

    connected = serializers.BooleanField(
        help_text=_("Info about whether the app can connect to the database")
    )


class RedisConnectionSerializer(serializers.Serializer):
    """
    Serializer for information about the Redis connection
    """

    connected = serializers.BooleanField(
        help_text=_("Info about whether the app can connect to Redis")
    )


class StatusSerializer(serializers.Serializer):
    """
    Serializer for the status information of the app
    """

    versions = VersionSerializer(
        help_text=_("Version information of Pulp components"),
        many=True
    )

    online_workers = WorkerSerializer(
        help_text=_("List of online workers known to the application. An online worker is actively "
                    "heartbeating and can respond to new work"),
        many=True
    )

    missing_workers = WorkerSerializer(
        help_text=_("List of missing workers known to the application. A missing worker is a "
                    "worker that was online, but has now stopped heartbeating and has potentially "
                    "died"),
        many=True
    )

    database_connection = DatabaseConnectionSerializer(
        help_text=_("Database connection information")
    )

    redis_connection = RedisConnectionSerializer(
        help_text=_("Redis connection information")
    )
