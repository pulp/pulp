from types import SimpleNamespace

TASKING_CONSTANTS = SimpleNamespace(
    # The prefix provided to normal worker entries in the workers table
    WORKER_PREFIX='reserved_resource_worker',
    # The name of resource manager entries in the workers table
    RESOURCE_MANAGER_WORKER_NAME='resource_manager',
    # The amount of time (in seconds) between process wakeups to "heartbeat" and perform
    # their tasks.
    PULP_PROCESS_HEARTBEAT_INTERVAL=5,
    # The amount of time (in seconds) after which a Celery process is considered missing.
    PULP_PROCESS_TIMEOUT_INTERVAL=25
)
