from datetime import datetime, timedelta

from pulp.server.db.model.base import Model
from pulp.server.db.model.reaper_base import ReaperMixin


class CeleryResult(Model, ReaperMixin):
    """
    Model reference to the Celery Results backend.
    """

    collection_name = 'celery_taskmeta'
    unique_indices = tuple()

    @classmethod
    def reap_old_documents(cls, config_days):
        """
        Delete old Celery task results from the celery_taskmeta collection.

        This overrides the inherited classmethod provided by ReaperMixin. The default
        functionality is not correct because Celery overrides the use of `_id` in the
        celery_taskmeta collection.

        :param config_days: Remove all records older than the number of days set by config_days.
        :type config_days: float
        """
        # Remove all objects older than the epoch time encoded in last_valid_date_done
        last_valid_date_done = datetime.utcnow() - timedelta(days=config_days)
        collection = cls.get_collection()
        collection.remove({'date_done': {'$lt': last_valid_date_done}})
