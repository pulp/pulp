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
