# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import unittest

import base

class TestImporter(unittest.TestCase):

    def test_load_all_modules(self):
        """
        Loads all modules in pulp to make sure they are captured during coverage tracking.
        """

        for root, sub_folders, files in os.walk(base.srcdir):
            for file in files:

                # Quick sanity checks for the stability of the coverage plugin
                if not file.endswith('.py'):
                    continue

                if '.egg' in file:
                    continue

                if '__init__' in file:
                    continue

                # Convert the file name into a format suitable for import
                full_path = root + '/' + file
                short_path = full_path[full_path.index('src') + 4:] # everything after src is package + module
                short_path = short_path[:-3] # strip off the .py
                module_name = short_path.replace('/', '.') # turn into module notation

                try:
                    __import__(module_name)
                except:
                    pass
