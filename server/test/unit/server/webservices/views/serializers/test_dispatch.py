import unittest

from pulp.devel.unit.util import compare_dict
from pulp.server.webservices.views.serializers import dispatch


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
