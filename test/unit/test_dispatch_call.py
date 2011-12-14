# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../common/'))

import testutil

from pulp.server.dispatch.call import CallReport, CallRequest

# call test api ----------------------------------------------------------------

class Call(object):
    """
    Test call functor
    """

    def __init__(self):
        self.args = []
        self.kwargs = {}

    def __call__(self, *args, **kwargs):
        self.args.extend(args)
        self.kwargs.update(kwargs)

# call request testing ---------------------------------------------------------

class CallRequestTests(testutil.PulpTest):

    def test_call_request_instantiation(self):
        try:
            call = Call()
            call_request = CallRequest(call)
        except Exception, e:
            self.fail(e.message)
