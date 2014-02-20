# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server import exceptions
from pulp.server.managers.schedule import utils
from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController


class ScheduleResource(JSONController):
    def _get(self, schedule_id):
        """
        Gets and returns a schedule by ID, in dict form suitable for json
        serialization and end-user presentation. Raises MissingResource if the
        schedule is not found.

        :param schedule_id: unique ID of a schedule
        :type  schedule_id: basestring

        :return:    dictionary representing the schedule
        :rtype:     dict

        :raise: pulp.server.exceptions.MissingResource
        """
        try:
            schedule = next(iter(utils.get([schedule_id])))
        except StopIteration:
            raise exceptions.MissingResource(schedule_id=schedule_id)

        ret = schedule.for_display()
        ret.update(serialization.link.current_link_obj())
        return self.ok(ret)
