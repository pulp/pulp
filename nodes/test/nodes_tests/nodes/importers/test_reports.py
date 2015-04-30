
from unittest import TestCase

from pulp.server.content.sources.model import DownloadReport, DownloadDetails

from pulp_node.error import ErrorList
from pulp_node.importers.reports import SummaryReport
from pulp_node.error import NodeError


class TestSummaryReport(TestCase):

    def test__init__(self):
        # test
        report = SummaryReport()

        # validation
        self.assertTrue(isinstance(report.errors, ErrorList))
        self.assertTrue(isinstance(report.sources, DownloadReport))

    def test_dict(self):
        report = SummaryReport()
        report.errors.append(NodeError(1, A=1, B=2))
        report.errors.append(NodeError(2, A=10, B=20))
        report.sources.total_passes = 1
        report.sources.total_sources = 10

        details = DownloadDetails()
        details.total_succeeded = 98
        details.total_failed = 2
        report.sources.downloads['content-world'] = details

        details = DownloadDetails()
        details.total_succeeded = 999999
        details.total_failed = 0
        report.sources.downloads['content-galaxy'] = details

        # test
        d = report.dict()

        # validation
        expected = {
            'sources': {
                'downloads': {
                    'content-world': {'total_failed': 2, 'total_succeeded': 98},
                    'content-galaxy': {'total_failed': 0, 'total_succeeded': 999999}
                },
                'total_sources': 10
            },
            'errors': [
                {'details': {'A': 1, 'B': 2}, 'error_id': 1},
                {'details': {'A': 10, 'B': 20}, 'error_id': 2}
            ]
        }
        self.assertEqual(d, expected)