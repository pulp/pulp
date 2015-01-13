"""
Contains DTOs to describe events.
"""

from mongoengine.queryset import DoesNotExist
import celery

from pulp.server.db.model.dispatch import TaskStatus


# These types are used to form AMQP message topic names, so they must be
# dot-delimited.

TYPE_REPO_PUBLISH_STARTED = 'repo.publish.start'
TYPE_REPO_PUBLISH_FINISHED = 'repo.publish.finish'

TYPE_REPO_SYNC_STARTED = 'repo.sync.start'
TYPE_REPO_SYNC_FINISHED = 'repo.sync.finish'

# Please keep the following in alphabetical order
# (feel free to change this if there's a simpler way)
ALL_EVENT_TYPES = (TYPE_REPO_PUBLISH_FINISHED, TYPE_REPO_PUBLISH_STARTED,
                   TYPE_REPO_SYNC_FINISHED, TYPE_REPO_SYNC_STARTED,)


class Event(object):

    def __init__(self, event_type, payload):
        self.event_type = event_type
        self.payload = payload
        try:
            task_id = celery.current_task.request.id
            self.call_report = TaskStatus.objects.get(task_id=task_id)
        except (AttributeError, DoesNotExist):
            self.call_report = None

    def __str__(self):
        return 'Event: Type [%s] Payload [%s]' % (self.event_type, self.payload)

    def data(self):
        """
        Generate a data report for this event.
        @return: dictionary of this event's fields
        @rtype: dict
        """
        d = {'event_type': self.event_type,
             'payload': self.payload,
             'call_report': self.call_report}
        return d
