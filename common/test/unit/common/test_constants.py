# -*- coding: utf-8 -*-

import unittest

from pulpcore.common import constants


class TestConstants(unittest.TestCase):
    """
    This class contains tests for the pulpcore.common.constants configuration.
    """

    def test_default_ca_path(self):
        self.assertTrue(constants.DEFAULT_CA_PATH is not None)
