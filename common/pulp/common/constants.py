# -*- coding: utf-8 -*-

# key used in a repository's "notes" field with a value describing what type
# of content is in the repository.
REPO_NOTE_TYPE_KEY = '_repo-type'

# Maps user entered query sort parameters to the pymongo representation
SORT_ASCENDING = 'ascending'
SORT_DESCENDING = 'descending'
# We are using constant values of pymongo.ASCENDING and pymongo.DESCENDING
# to avoid every consumer having a dependency on pymongo just for these constants.
SORT_DIRECTION = {
    SORT_ASCENDING: 1,
    SORT_DESCENDING: -1,
}

# Strings for repository history filters
REPO_HISTORY_FILTER_LIMIT = 'limit'
REPO_HISTORY_FILTER_SORT = 'sort'
REPO_HISTORY_FILTER_START_DATE = 'start_date'
REPO_HISTORY_FILTER_END_DATE = 'end_date'

# Maximum number of units that should be displayed at one time by the command line
DISPLAY_UNITS_DEFAULT_MAXIMUM = 100

# call states ------------------------------------------------------------------

CALL_WAITING_STATE = 'waiting'
CALL_SKIPPED_STATE = 'skipped'
CALL_ACCEPTED_STATE = 'accepted'
CALL_RUNNING_STATE = 'running'
CALL_SUSPENDED_STATE = 'suspended'
CALL_FINISHED_STATE = 'finished'
CALL_ERROR_STATE = 'error'
CALL_CANCELED_STATE = 'canceled'

CALL_INCOMPLETE_STATES = (CALL_WAITING_STATE, CALL_ACCEPTED_STATE, CALL_RUNNING_STATE,
                          CALL_SUSPENDED_STATE)
CALL_COMPLETE_STATES = (CALL_SKIPPED_STATE, CALL_FINISHED_STATE, CALL_ERROR_STATE,
                        CALL_CANCELED_STATE)
CALL_STATES = (CALL_WAITING_STATE, CALL_SKIPPED_STATE, CALL_ACCEPTED_STATE, CALL_RUNNING_STATE,
               CALL_SUSPENDED_STATE, CALL_FINISHED_STATE, CALL_ERROR_STATE, CALL_CANCELED_STATE)

# this constant is used to determine which content source is the primary
# source, vs an alternate source.  Note that this field will go away in Pulp
# 3.0 as part of https://bugzilla.redhat.com/show_bug.cgi?id=1160410

PRIMARY_ID = '___/primary/___'

# this is used by both platform and plugins to find the default CA path
DEFAULT_CA_PATH = '/etc/pki/tls/certs/ca-bundle.crt'

# celerybeat constants

# Scheduler worker name
SCHEDULER_WORKER_NAME = 'scheduler'
# Constant used as the default wait time for celerybeat instances with no lock
CELERY_TICK_DEFAULT_WAIT_TIME = 90
# Constant used to determine whether a CeleryBeatLock should be removed due to age
CELERYBEAT_LOCK_MAX_AGE = 200
# The amount of time in seconds before a Celery process is considered missing
CELERY_TIMEOUT_SECONDS = 300
# The interval in seconds for which the Celery Process monitor thread sleeps between
# checking for missing Celery processes.
CELERY_CHECK_INTERVAL = 60
# The maximum number of seconds that will ever elapse before the scheduler looks for
# new or changed schedules
CELERY_MAX_INTERVAL = 90

# resource manager constants

# Resource manager worker name
RESOURCE_MANAGER_WORKER_NAME = 'resource_manager'
