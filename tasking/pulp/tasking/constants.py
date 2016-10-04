from types import SimpleNamespace

TASKING_CONSTANTS = SimpleNamespace(
    # The interval in seconds for which the Celery Process monitor thread sleeps between
    # checking for missing Celery processes.
    CELERY_CHECK_INTERVAL=60,
    # Resource manager worker name
    RESOURCE_MANAGER_WORKER_NAME='resource_manager'
)
