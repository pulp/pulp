from pulp.server import exceptions
from pulp.server.managers.schedule import utils
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController


class ScheduleResource(JSONController):
    def _get(self, schedule_id):
        try:
            schedule = utils.get([schedule_id])[0]
        except IndexError:
            raise exceptions.MissingResource(schedule_id=schedule_id)

        ret = schedule.for_display()
        ret.update(serialization.link.current_link_obj())
        return self.ok(ret)
