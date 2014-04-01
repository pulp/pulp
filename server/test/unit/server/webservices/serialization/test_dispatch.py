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

import unittest

from pulp.devel.unit.util import compare_dict
from pulp.server.webservices.serialization import dispatch


class TestSpawnedTasks(unittest.TestCase):

    def test_spawned_tasks(self):
        result = dispatch.spawned_tasks({'spawned_tasks': ['apple']})
        target_dict = {'spawned_tasks': [dispatch.link_obj('/pulp/api/v2/tasks/apple/')]}
        target_dict['spawned_tasks'][0].update({'task_id': 'apple'})
        compare_dict(result, target_dict)

    def test_spawned_tasks_empty(self):
        result = dispatch.spawned_tasks({'spawned_tasks': []})
        target_dict = {'spawned_tasks': []}
        compare_dict(result, target_dict)

    def test_spawned_tasks_none(self):
        result = dispatch.spawned_tasks({'spawned_tasks': None})
        target_dict = {'spawned_tasks': []}
        compare_dict(result, target_dict)
