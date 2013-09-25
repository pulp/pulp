# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
"""
This module contains tests for the pulp.server.webservices.dispatch module.
"""
import mock

import base


class TestTaskResource(base.PulpWebserviceTests):
    """
    Test the TaskResource class.
    """
    @mock.patch('pulp.server.tasks.controller.revoke', autospec=True)
    def test_DELETE_celery_task(self, revoke):
        """
        Test the DELETE() method with a UUID that does not correspond to a UUID that the
        coordinator is aware of. This should cause a revoke call to Celery's Controller.
        """
        task_id = '1234abcd'
        url = '/v2/tasks/%s/'

        self.delete(url % task_id)

        revoke.assert_called_once_with(task_id, terminate=True)
