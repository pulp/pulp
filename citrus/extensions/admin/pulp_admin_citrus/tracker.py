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


from okaara.prompt import COLOR_GREEN, COLOR_RED, MOVE_UP, CLEAR_REMAINDER


class ProgressTracker:

    def __init__(self, prompt):
        self.prompt = prompt
        self.next_step = 0
        self.details = None
        self.OK = prompt.color('OK', COLOR_GREEN)
        self.FAILED = prompt.color('FAILED', COLOR_RED)

    def reset(self):
        self.next_step = 0
        self.details = None

    def display(self, report):
        self.display_steps(report['steps'])
        self.display_details(report['details'])

    def display_steps(self, steps):
        num_steps = len(steps)
        self.backup()
        for i in range(self.next_step, num_steps):
            self.write_step(steps[i])
            self.next_step = i

    def backup(self):
        lines = 1
        if self.details:
            lines += len(self.details.split('\n'))
        self.prompt.move(MOVE_UP % lines)
        self.prompt.clear(CLEAR_REMAINDER)

    def write_step(self, step):
        name, status = step
        if status is None:
            self.prompt.write(name)
            return
        if status:
            status = self.OK
        else:
            status = self.FAILED
        self.prompt.write('%-40s[ %s ]' % (name, status))

    def display_details(self, details):
        action = details.get('action')
        package = details.get('package')
        error = details.get('error')
        self.details = None
        if action:
            self.details = '%+12s: %s' % (action, package)
            self.prompt.write(self.details)
            return
        if error:
            action = 'Error'
            self.details = '%+12s: %s' % (action, error)
            self.prompt.write(self.details, COLOR_RED)