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

import os
import sys
import time

from unittest import TestCase

from okaara.prompt import Prompt, CLEAR_REMAINDER, MOVE_UP

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../../extensions/admin')
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../../src')

from pulp.citrus.progress import ProgressReport
from pulp_admin_citrus.tracker import ProgressTracker



class TestReport(ProgressReport):

    def __init__(self, prompt):
        ProgressReport.__init__(self)
        self.tracker = ProgressTracker(prompt)

    def _updated(self):
        ProgressReport._updated(self)
        if self.tracker.lines_written:
            time.sleep(.25)
        self.tracker.display(self.dict())


class TestProgress(TestCase):

    def _test_2(self):
        r = TestReport(Prompt())
        r.push_step('Initialize')
        r.push_step('Merge')
        r.push_step('Purge')
        r.push_step('Synchronize')
        N = 20
        r.push_step('Download', N)
        for i in range(0, N):
            r.set_action('wget', 'http://pulp.com/unit_%d' % i)
        r.push_step('Import')
        r2 = ProgressReport(r)
        r2.push_step('Read Manifest')
        r2.push_step('Read Units', N)
        for i in range(0, N):
            r2.set_action('wget', 'http://pulp.upstream.com/unit_%d' % i)
        r2.push_step('Purge Orphans')
        r.set_status(ProgressReport.SUCCEEDED)

    def test_3(self):
        r = TestReport(Prompt())
        r.push_step('Initialize')
        r.push_step('Merge')
        r.push_step('Purge')
        r.push_step('Synchronize')
        N = 20
        r.push_step('Download', N)
        for i in range(0, N):
            r.set_action('wget', 'http://pulp.com/unit_%d' % i)
            if i == (N-2):
                r.error('This is my test error')
                break
        r.push_step('Import')
        r2 = ProgressReport(r)
        r2.push_step('Read Manifest')
        r2.push_step('Read Units', N)
        for i in range(0, N):
            r2.set_action('wget', 'http://pulp.upstream.com/unit_%d' % i)
            if i == (N-2):
                r.error('This is my test error')
                break
        r2.push_step('Purge Orphans')
        r.set_status(ProgressReport.SUCCEEDED)
