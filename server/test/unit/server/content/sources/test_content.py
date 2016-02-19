import inspect

from pulp.common import error_codes
from pulp.common.compat import unittest
from pulp.server.content.sources.model import ContentSource, RefreshReport
from pulp.server.controllers.content import ContentSourcesRefreshStep

import mock
from pulp.server.exceptions import PulpCodedException


class TestRefreshStepProcessMain(unittest.TestCase):
    def setUp(self):
        self.conduit = mock.MagicMock()
        self.step = ContentSourcesRefreshStep(self.conduit)
        self.source = ContentSource('foo', {'name': 'foo'})
        self.report = RefreshReport('foo', 'http://foo.com')
        self.report.succeeded = True

    def test_calls_refresh(self):
        """
        Ensure the source's refresh method gets called with the right args.
        """
        with mock.patch.object(self.source, 'refresh', spec_set=True) as mock_refresh:
            mock_refresh.return_value = [self.report]
            self.step.process_main(item=self.source)

        # assert that the real function takes the args we think it takes
        self.assertEqual(inspect.getargspec(ContentSource.refresh).args, ['self'])
        # then make sure we pass the right args
        mock_refresh.assert_called_once_with()

    def test_report_failed_raises_exception(self):
        """
        Ensure that a pulp coded exception is raised with the correct error code.
        """
        self.report.succeeded = False

        with mock.patch.object(self.source, 'refresh', spec_set=True) as mock_refresh:
            mock_refresh.return_value = [self.report]
            with self.assertRaises(PulpCodedException) as assertion:
                self.step.process_main(item=self.source)

        self.assertEqual(assertion.exception.error_code, error_codes.PLP0031)
