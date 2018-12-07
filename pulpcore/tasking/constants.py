from types import SimpleNamespace

TASKING_CONSTANTS = SimpleNamespace(
    # The prefix provided to normal worker entries in the workers table
    WORKER_PREFIX='reserved_resource_worker',
    # The name of resource manager entries in the workers table
    RESOURCE_MANAGER_WORKER_NAME='resource_manager',
    # The amount of time (in seconds) after which a worker process is considered missing.
    WORKER_TTL=30,
    # The amount of time (in seconds) between checks
    JOB_MONITORING_INTERVAL=5,
    # The Redis key used to force-kill a job
    KILL_KEY="rq:jobs:kill"
)
