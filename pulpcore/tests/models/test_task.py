from django.db.models import ProtectedError
from django.test import TestCase

from pulpcore.app.models import ReservedResource, Task, TaskReservedResource, Worker


class TaskTestCase(TestCase):
    def test_delete_with_reserved_resources(self):
        """
        Tests that attempting to delete a task with reserved resources will raise
        a ProtectedError
        """
        task = Task.objects.create()
        worker = Worker.objects.create(name="test_worker")
        resource = ReservedResource.objects.create(resource="test",
                                                   worker=worker)
        TaskReservedResource.objects.create(task=task, resource=resource)
        with self.assertRaises(ProtectedError):
            task.delete()
        task.release_resources()
        task.delete()
        self.assertFalse(Task.objects.filter(id=task.id).exists())
