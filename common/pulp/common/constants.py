from types import SimpleNamespace


TASK_STATES = SimpleNamespace(
    WAITING='waiting',
    SKIPPED='skipped',
    RUNNING='running',
    COMPLETED='completed',
    FAILED='failed',
    CANCELED='canceled'
)

TASK_FINAL_STATES = (TASK_STATES.SKIPPED, TASK_STATES.COMPLETED, TASK_STATES.FAILED,
                     TASK_STATES.CANCELED)
TASK_INCOMPLETE_STATES = (TASK_STATES.WAITING, TASK_STATES.RUNNING)
