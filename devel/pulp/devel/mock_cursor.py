# -*- coding: utf-8 -*-
#
# Copyright © 2011-2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Mock cursor object used to aid in testing methods that reutn pymongo cursors
"""
class MockCursor():
    def __init__(self, contents):
        self.contents = contents
        self.num = 0

    def __iter__(self):
        return self

    def count(self):
        return len(self.contents)

    def next(self):
        if self.num < len(self.contents):
            current = self.contents[self.num]
            self.num += 1
            return current
        else:
            raise StopIteration()
