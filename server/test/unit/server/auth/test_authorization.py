import unittest

from pulp.server.auth import authorization


class TestAuthorization(unittest.TestCase):

    def test_module_level_attributes(self):
        """
        Assert that the expected module level variables are correct.
        """
        self.assertEqual(authorization.CREATE, 0)
        self.assertEqual(authorization.READ, 1)
        self.assertEqual(authorization.UPDATE, 2)
        self.assertEqual(authorization.DELETE, 3)
        self.assertEqual(authorization.EXECUTE, 4)
        expected_op_names = ['CREATE', 'READ', 'UPDATE', 'DELETE', 'EXECUTE']
        self.assertEqual(authorization.OPERATION_NAMES, expected_op_names)

    def test__lookup_operation_name(self):
        """
        Test the _lookup_operation_name function
        """
        _lookup = authorization._lookup_operation_name
        self.assertEqual(_lookup(0), 'CREATE')
        self.assertEqual(_lookup(1), 'READ')
        self.assertEqual(_lookup(2), 'UPDATE')
        self.assertEqual(_lookup(3), 'DELETE')
        self.assertEqual(_lookup(4), 'EXECUTE')
        invalid_operation_value = 1000
        self.assertRaises(KeyError, _lookup, invalid_operation_value)
