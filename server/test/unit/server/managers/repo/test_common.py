import unittest

from pulp.server.managers.repo._common import to_transfer_repo


class TestToTransferRepo(unittest.TestCase):

    def test_to_transfer_repo(self):
        data = {
            'id': 'foo',
            'display_name': 'bar',
            'description': 'baz',
            'notes': 'qux',
            'content_unit_counts': {'units': 1},
            'last_unit_added': 1,
            'last_unit_removed': 2
        }

        repo = to_transfer_repo(data)
        self.assertEquals('foo', repo.id)
        self.assertEquals('bar', repo.display_name)
        self.assertEquals('baz', repo.description)
        self.assertEquals('qux', repo.notes)
        self.assertEquals({'units': 1}, repo.content_unit_counts)
        self.assertEquals(1, repo.last_unit_added)
        self.assertEquals(2, repo.last_unit_removed)

    def test_to_transfer_repo_unit_timestamps_not_specified(self):
        data = {
            'id': 'foo',
            'display_name': 'bar',
            'description': 'baz',
            'notes': 'qux',
            'content_unit_counts': {'units': 1}
        }

        repo = to_transfer_repo(data)
        self.assertEquals(None, repo.last_unit_added)
        self.assertEquals(None, repo.last_unit_removed)
