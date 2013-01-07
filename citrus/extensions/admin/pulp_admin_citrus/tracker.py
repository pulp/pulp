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


from okaara.prompt import COLOR_GREEN, COLOR_YELLOW, COLOR_RED, MOVE_UP, CLEAR_REMAINDER


class ProgressTracker:

    def __init__(self, prompt):
        self.prompt = prompt
        self.lines_written = 0

    def _erase(self):
        self.prompt.move(MOVE_UP % self.lines_written)
        self.prompt.clear(CLEAR_REMAINDER)

    def display(self, report):
        if self.lines_written:
            self._erase()
        skin = ReportSkin(self.prompt, report)
        output = skin.render()
        self.prompt.write(output, new_line=False, skip_wrap=True)
        self.lines_written = (len(output.split('\n'))-1)


class ReportSkin:

    def __init__(self, prompt, report, indent=0):
        self.prompt = prompt
        self.report = report
        self.indent = '%-*s' % (indent * 2, '')
        self._indent = indent

    def color(self, s, color):
        return self.prompt.color(s, color)

    def _steps(self):
        s = []
        for step in self.report['steps']:
            name, status, action_ratio = step
            width = (40 - len(self.indent))
            if isinstance(status, bool):
                if status:
                    status = self.color('OK', COLOR_GREEN)
                else:
                    status = self.color('FAILED', COLOR_RED)
                s.append(self.indent + '%-*s[ %s ]' % (width, name, status))
                continue
            if action_ratio[1]:
                pct = float(action_ratio[0]) / float(action_ratio[1])
                bar = self.progress_bar(pct)
                s.append(self.indent + '%-*s%s' % (width, name, bar))
                continue
            if status is None:
                s.append(name)
                continue
        return '\n'.join(s)

    def _action(self):
        step = self.report['steps'][-1]
        details = self.report['action']
        action = details.get('action')
        subject = details.get('subject')
        error = details.get('error')
        if action:
            action_ratio = step[2]
            if action_ratio[1]:
                return self.indent + '(%d/%d): %s on: %s' % \
                    (action_ratio[0], action_ratio[1], action, subject)
            else:
                return self.indent + '%s on: %s' % (action, subject)
        if error:
            action = self.color('Error', COLOR_RED)
            return self.indent + '%+12s: %s' % (action, error)
        return ''

    def _nested_report(self):
        nested_report = self.report.get('nested_report')
        if nested_report:
            skin = ReportSkin(self.prompt, nested_report, self._indent+1)
            return self.indent + skin.render()
        else:
            return ''

    def progress_bar(self, pct, granularity=10):
        if pct > 1.0: pct = 1.0
        fill = ''.rjust(int(granularity*pct), '=')
        bar = '[%-*s] %d%%' % (granularity, fill, pct * 100)
        return self.color(bar, COLOR_YELLOW)

    def render(self):
        s = []
        s.append(self._steps())
        s.append(self._action())
        s.append(self._nested_report())
        return '\n'.join(s)

    def __str__(self):
        return self.render()