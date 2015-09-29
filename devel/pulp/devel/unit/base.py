import logging
import unittest

import mock
import okaara.prompt

from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from pulp.client.extensions.core import ClientContext, PulpPrompt, PulpCli
from pulp.client.extensions.exceptions import ExceptionHandler
from pulp.common.config import Config


# Copy the config here from pulp.client.admin.config so we don't have to start an import chain
# that pulls in NamedTuple in tests on Python 2.4
DEFAULT_CONFIG = {
    'server': {
        'host': 'localhost.localdomain',
        'port': '443',
        'api_prefix': '/pulp/api',
        'verify_ssl': 'true',
        'ca_path': '/etc/pki/tls/certs/ca-bundle.crt',
        'upload_chunk_size': '1048576',
    },
    'client': {
        'role': 'admin'
    },
    'filesystem': {
        'extensions_dir': '/usr/lib/pulp/admin/extensions',
        'id_cert_dir': '/tmp/pulp_test',
        'id_cert_filename': 'user-cert.pem',
        'upload_working_dir': '/tmp/pulp_test/uploads',
    },
    'output': {
        'poll_frequency_in_seconds': '.5',
        'enable_color': 'true',
        'wrap_to_terminal': 'false',
        'wrap_width': '80',
    },
}


class PulpClientTests(unittest.TestCase):
    """
    Base unit test class for all extension unit tests.
    """

    def setUp(self):
        super(PulpClientTests, self).setUp()

        self.config = Config(DEFAULT_CONFIG)

        self.server_mock = mock.Mock()
        self.pulp_connection = PulpConnection('', server_wrapper=self.server_mock)
        self.bindings = Bindings(self.pulp_connection)

        # Disabling color makes it easier to grep results since the character codes aren't there
        self.recorder = okaara.prompt.Recorder()
        self.prompt = PulpPrompt(enable_color=False, output=self.recorder, record_tags=True)

        self.logger = logging.getLogger('pulp')
        self.exception_handler = ExceptionHandler(self.prompt, self.config)

        self.context = ClientContext(self.bindings, self.config, self.logger, self.prompt,
                                     self.exception_handler)

        self.cli = PulpCli(self.context)
        self.context.cli = self.cli


class PulpCeleryTaskTests(unittest.TestCase):
    """
    Base class for tests of webservice controllers.  This base is used to work around the
    authentication tests for each each method
    """

    def setUp(self):
        self.patch1 = mock.patch('pulp.server.db.models.TaskStatus')
        self.patch1.start()

    def tearDown(self):
        self.patch1.stop()
