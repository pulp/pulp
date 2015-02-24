from django.views.generic import View

from pulp.server import exceptions as pulp_exceptions
from pulp.server.managers.schedule import utils as schedule_utils
from pulp.server.webservices.views.util import generate_json_response


class ScheduleResource(View):
    """
    Base class for views that retrieve a single schedule by id.
    """
    def _get(self, schedule_id, resource_href):
        """
        Gets and returns a schedule by ID, in dict form suitable for json serialization and
        end-user presentation.

        :param resource_href: href of the schedule
        :type  resource_href: str
        :param schedule_id: unique ID of a schedule
        :type  schedule_id: basestring

        :return:    dictionary representing the schedule
        :rtype:     dict

        :raise pulp.server.exceptions.MissingResource: if schedule is not found
        """

        # If schedule_id is not a valid bson ObjectId, this will raise InvalidValue. If the
        # schedule_id is a valid bson ObjectId but doesn't exist it will raise StopIteration.
        # Either should be a 404.
        try:
            schedule = next(iter(schedule_utils.get([schedule_id])))
        except (StopIteration, pulp_exceptions.InvalidValue):
            raise pulp_exceptions.MissingResource(schedule_id=schedule_id)

        ret = schedule.for_display()
        ret['_href'] = resource_href
        return generate_json_response(ret)
