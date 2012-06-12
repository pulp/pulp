#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


import base

import pulp.bindings.exceptions as exceptions
from pulp.client.extensions.core import TAG_FAILURE, TAG_PARAGRAPH
import pulp.client.extensions.exceptions as handler
from pulp.client.arg_utils import InvalidConfig

class ExceptionsLoaderTest(base.PulpClientTests):
    """
    All tests in this class use the exception handler configured in the
    PulpV2ClientTest base class as the test object.

    The tests on each individual handle method will do a weak but sufficient
    check to ensure the correct message is output.
    """

    def test_handle_exception(self):
        """
        Tests the high level call that branches based on exception type for all types.
        """

        # For each exception type, check that the proper code is returned and
        # that a failure message has been output. For simplicity in those tests,
        # reset the tags after each run.

        code = self.exception_handler.handle_exception(exceptions.BadRequestException({}))
        self.assertEqual(code, handler.CODE_BAD_REQUEST)
        self.assertEqual(3, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.ConflictException({}))
        self.assertEqual(code, handler.CODE_CONFLICT)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.ConnectionException({}))
        self.assertEqual(code, handler.CODE_CONNECTION_EXCEPTION)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.NotFoundException({'resources' : {'repo_id' : 'foo'}}))
        self.assertEqual(code, handler.CODE_NOT_FOUND)
        self.assertEqual(2, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.PermissionsException({}))
        self.assertEqual(code, handler.CODE_PERMISSIONS_EXCEPTION)
        self.assertEqual(2, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.assertEqual(TAG_PARAGRAPH, self.prompt.get_write_tags()[1])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(exceptions.PulpServerException({}))
        self.assertEqual(code, handler.CODE_PULP_SERVER_EXCEPTION)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(InvalidConfig('Test Message'))
        self.assertEqual(code, handler.CODE_INVALID_CONFIG)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

        code = self.exception_handler.handle_exception(Exception({}))
        self.assertEqual(code, handler.CODE_UNEXPECTED)
        self.assertEqual(1, len(self.prompt.tags))
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.prompt.tags = []

    def test_bad_request_invalid_values(self):
        """
        Tests the invalid values classification of bad request exceptions.
        """

        # Test
        e = exceptions.BadRequestException({'property_names' : ['foo']})
        code = self.exception_handler.handle_bad_request(e)
        
        # Verify
        self.assertEqual(code, handler.CODE_BAD_REQUEST)
        self.assertTrue('properties were invalid' in self.recorder.lines[0])
        self.assertTrue('foo' in self.recorder.lines[0])

    def test_bad_request_missing_properties(self):
        """
        Tests the missing properties classification of bad request exceptions.
        """

        # Test
        e = exceptions.BadRequestException({'missing_property_names' : ['foo']})
        code = self.exception_handler.handle_bad_request(e)

        # Verify
        self.assertEqual(code, handler.CODE_BAD_REQUEST)
        self.assertTrue('not provided' in self.recorder.lines[0])
        self.assertTrue('foo' in self.recorder.lines[0])

    def test_bad_request_other(self):
        """
        Tests a bad request with no classification.
        """

        # Test
        e = exceptions.BadRequestException({})
        code = self.exception_handler.handle_bad_request(e)

        # Verify
        self.assertEqual(code, handler.CODE_BAD_REQUEST)
        self.assertTrue('incorrect' in self.recorder.lines[0])

    def test_not_found(self):

        # Test
        e = exceptions.NotFoundException({'resources' : {'repo_id' : 'foo'}})
        code = self.exception_handler.handle_not_found(e)

        # Verify
        self.assertEqual(code, handler.CODE_NOT_FOUND)
        self.assertTrue('foo' in self.recorder.lines[2])

    def test_conflict_resource(self):
        """
        Tests the conflict classification that represents a duplicate resource.
        """

        # Test
        e = exceptions.ConflictException({'resource_id' : 'foo'})
        code = self.exception_handler.handle_conflict(e)

        # Verify
        self.assertEqual(code, handler.CODE_CONFLICT)
        self.assertTrue('resource' in self.recorder.lines[0])
        self.assertTrue('foo' in self.recorder.lines[0])

    def test_conflict_operation(self):
        """
        Tests the conflict classification that represents a conflicting operation.
        """

        # Test
        reasons = [ {'resource_id' : 'foo', 'resource_type' : 'bar', 'operation' : 'baz'}]
        e = exceptions.ConflictException({'reasons' : reasons})
        code = self.exception_handler.handle_conflict(e)

        # Verify
        self.assertEqual(code, handler.CODE_CONFLICT)
        self.assertTrue('operation' in self.recorder.lines[0])
        self.assertTrue('foo' in self.recorder.lines[0])
        self.assertTrue('bar' in self.recorder.lines[0])
        self.assertTrue('baz' in self.recorder.lines[0])

    def test_conflict_other(self):
        """
        Tests a conflict that does not contain classificationd data.
        """

        # Test
        e = exceptions.ConflictException({})
        code = self.exception_handler.handle_conflict(e)

        # Verify
        self.assertEqual(code, handler.CODE_CONFLICT)
        self.assertTrue('unexpected', self.recorder.lines[0])

    def test_server_error(self):
        """
        Tests a general server error.
        """

        # Test
        e = exceptions.PulpServerException({})
        code = self.exception_handler.handle_server_error(e)

        # Verify
        self.assertEqual(code, handler.CODE_PULP_SERVER_EXCEPTION)
        self.assertTrue('internal error' in self.recorder.lines[0])

    def test_connection_error(self):
        """
        Tests a client-side connection error.
        """

        # Test
        e = exceptions.ConnectionException()
        code = self.exception_handler.handle_connection_error(e)

        # Verify
        self.assertEqual(code, handler.CODE_CONNECTION_EXCEPTION)
        self.assertTrue('contact the server' in self.recorder.lines[0])

    def test_permission(self):
        """
        Tests a client-side error when the connection is rejected due to auth reasons.
        """

        # Test
        e = exceptions.PermissionsException()
        code = self.exception_handler.handle_permission(e)

        # Verify
        self.assertEqual(code, handler.CODE_PERMISSIONS_EXCEPTION)
        self.assertTrue('Authentication' in self.recorder.lines[0])
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])
        self.assertTrue('certificate' in self.recorder.lines[2]) # skip blank line
        self.assertEqual(TAG_PARAGRAPH, self.prompt.get_write_tags()[1])

    def test_invalid_config(self):
        """
        Tests a client-side argument parsing errror.
        """

        # Test
        e = InvalidConfig('Expected')
        code = self.exception_handler.handle_invalid_config(e)

        # Verify
        self.assertEqual(code, handler.CODE_INVALID_CONFIG)
        self.assertEqual('Expected', self.recorder.lines[0].strip())
        self.assertEqual(TAG_FAILURE, self.prompt.get_write_tags()[0])

    def test_unexpected(self):
        """
        Tests the handling of any non-client defined exception class.
        """

        # Test
        e = Exception()
        code = self.exception_handler.handle_unexpected(e)

        # Verify
        self.assertEqual(code, handler.CODE_UNEXPECTED)
        self.assertTrue('unexpected' in self.recorder.lines[0])