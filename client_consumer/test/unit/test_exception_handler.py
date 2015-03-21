from pulp.bindings import exceptions as bindings_exceptions
from pulp.client.consumer.exception_handler import ConsumerExceptionHandler
from pulp.client.extensions import exceptions
from pulp.client.extensions.core import TAG_FAILURE
from pulp.devel.unit import base


class ConsumerExceptionHandlerTests(base.PulpClientTests):

    def setUp(self):
        super(ConsumerExceptionHandlerTests, self).setUp()

        self.handler = ConsumerExceptionHandler(self.prompt, self.config)

    def test_permission(self):
        """
        Tests a client-side error when the connection is rejected due to auth reasons.
        """
        # Test
        response_body = {'auth_error_code': 'authentication_failed'}
        e = bindings_exceptions.PermissionsException(response_body)
        e.error_message = "I've made a huge mistake."
        code = self.handler.handle_permission(e)

        # Verify
        self.assertEqual(code, exceptions.CODE_PERMISSIONS_EXCEPTION)
        self.assertTrue("I've made a huge mistake.\n" == self.recorder.lines[0])
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
