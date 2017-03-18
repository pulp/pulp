from types import SimpleNamespace


#: All valid task states.
TASK_STATES = SimpleNamespace(
    WAITING='waiting',
    SKIPPED='skipped',
    RUNNING='running',
    COMPLETED='completed',
    FAILED='failed',
    CANCELED='canceled'
)

#: Tasks in a final state have finished their work.
TASK_FINAL_STATES = (TASK_STATES.SKIPPED, TASK_STATES.COMPLETED, TASK_STATES.FAILED,
                     TASK_STATES.CANCELED)

#: Tasks in an incomplete state have not finished their work yet.
TASK_INCOMPLETE_STATES = (TASK_STATES.WAITING, TASK_STATES.RUNNING)

# The amount of time the migration script will wait to confirm that no processes are running.
# This is the 90s CELERY_TICK_DEFAULT_WAIT_TIME used in Pulp version < 2.12 and a 2s buffer.
# This ensures that the process check feature works correctly even in cases where a user
# forgot to restart pulp_celerybeat while upgrading from Pulp 2.11 or earlier.
MIGRATION_WAIT_TIME = 92
