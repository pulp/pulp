# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import mock

class FakeThread(mock.MagicMock):
    """
    In cases where our code starts a new thread, this can be used in unit tests
    to make that code run immediately in the current thread instead.
    """
    def __init__(self, target, args):
        """
        see threading.Thread for arg
        """
        super(FakeThread, self).__init__()
        self._target = target
        self._args = args

    def start(self, *args, **kwargs):
        """
        run the given function with the given args immediately without starting
        a new thread
        """
        self._target(*self._args)
