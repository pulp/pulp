import datetime
import unittest

from pulp.common import dateutils
from pulp.server.managers.repo._common import to_transfer_repo, _ensure_tz_specified


class TestToTransferRepo(unittest.TestCase):

    def test_to_transfer_repo(self):

        dt = dateutils.now_utc_datetime_with_tzinfo()
        data = {
            'id': 'foo',
            'display_name': 'bar',
            'description': 'baz',
            'notes': 'qux',
            'content_unit_counts': {'units': 1},
            'last_unit_added': dt,
            'last_unit_removed': dt
        }

        repo = to_transfer_repo(data)
        self.assertEquals('foo', repo.id)
        self.assertEquals('bar', repo.display_name)
        self.assertEquals('baz', repo.description)
        self.assertEquals('qux', repo.notes)
        self.assertEquals({'units': 1}, repo.content_unit_counts)
        self.assertEquals(dt, repo.last_unit_added)
        self.assertEquals(dt, repo.last_unit_removed)

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


class TestEnsureTzSpecified(unittest.TestCase):

    def test_tz_not_specified(self):
        dt = datetime.datetime.utcnow()
        new_date = _ensure_tz_specified(dt)
        self.assertEquals(new_date.tzinfo, dateutils.utc_tz())

    def test_none_object(self):
        dt = None
        new_date = _ensure_tz_specified(dt)
        self.assertEquals(new_date, None)

    def test_tz_specified(self):
        dt = datetime.datetime.now(dateutils.local_tz())
        new_date = _ensure_tz_specified(dt)
        self.assertEquals(new_date.tzinfo, dateutils.utc_tz())
