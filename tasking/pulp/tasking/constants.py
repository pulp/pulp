from types import SimpleNamespace

TASKING_CONSTANTS = SimpleNamespace(
    # The interval in seconds for which the Celery Process monitor thread sleeps between
    # checking for missing Celery processes.
    CELERY_CHECK_INTERVAL=60,
    # The interval in seconds during which the Celery Processes being monitored need to report a
    # hearbeat to be considered active.
    HEARTBEAT_MAX_AGE=200,
    # The interval in seconds with which a secondary celerybeat tries to acquire the lock
    # that is needed to be the primary celerybeat.
    CELERYBEAT_LOCK_RETRY_TIME=90,
    # The name of the resource manager entry in the workers table
    RESOURCE_MANAGER_WORKER_NAME='resource_manager',
    # The name of the celerybeat entry in the workers table
    CELERYBEAT_WORKER_NAME = 'celerybeat',
    # The maximum amount of time in seconds celerybeat sleeps before checking for more scheduled
    # work to dispatch.
    CELERYBEAT_MAX_SLEEP_INTERVAL=90,
    # The amount of time in seconds that a celerybeat lock is valid for. If the lock is older than
    # the value specified here, the process holding the lock is considered dead.
    CELERYBEAT_LOCK_MAX_AGE=200
)
