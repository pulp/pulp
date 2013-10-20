CELERY_RESULT_BACKEND = "mongodb"
CELERY_MONGODB_BACKEND_SETTINGS = {
    "host": "localhost",
    "database": "pulp_database",
    "taskmeta_collection": "celery_task_result"
}
