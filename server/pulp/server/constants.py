from pulp.server.config import config

LOCAL_STORAGE = "/var/lib/pulp/"

PULP_USER_METADATA_FIELDNAME = 'pulp_user_metadata'
PULP_DJANGO_SETTINGS_MODULE = 'pulp.server.webservices.settings'
PULP_STREAM_REQUEST_HEADER = 'Pulp-Stream-Request'
SUPER_USER_ROLE = 'super-users'

# The amount of time (in seconds) between process wakeups to "heartbeat" and perform their tasks.
# See https://pulp.plan.io/issues/3135#note-15 for info about this calculation.
PULP_PROCESS_HEARTBEAT_INTERVAL = int(config.getint('tasks', 'worker_timeout') / 5)

# The amount of time (in seconds) after which a Celery process is considered missing.
PULP_PROCESS_TIMEOUT_INTERVAL = config.getint('tasks', 'worker_timeout') - \
    PULP_PROCESS_HEARTBEAT_INTERVAL
