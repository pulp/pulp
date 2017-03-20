from types import SimpleNamespace

TASKING_CONSTANTS = SimpleNamespace(
    # The name of the resource manager entry in the workers table
    RESOURCE_MANAGER_WORKER_NAME='resource_manager',
    # The name of the celerybeat entry in the workers table
    CELERYBEAT_WORKER_NAME='celerybeat',
    # The amount of time (in seconds) between process wakeups to "heartbeat" and perform
    # their tasks.
    PULP_PROCESS_HEARTBEAT_INTERVAL=5,
    # The amount of time (in seconds) after which a Celery process is considered missing.
    PULP_PROCESS_TIMEOUT_INTERVAL=25
)
