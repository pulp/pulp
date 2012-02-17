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

"""
Defines Pulp additions to the okaara base classes. The subclasses
for the individual components that belong to each UI style
(e.g. commands, screens) can be found in extensions.py as they are meant to be
further subclassed by extensions.
"""

import math

from   okaara.cli import Cli
from   okaara.progress import ProgressBar, Spinner
import okaara.prompt
from   okaara.prompt import Prompt, WIDTH_TERMINAL

# -- constants ----------------------------------------------------------------

# Values used for tags in each of the rendering calls; these should be used
# in unit tests to verify the correct write call was made
TAG_TITLE = 'title'
TAG_DESCRIPTION = 'description'
TAG_MAP_LIST_ITEM = 'map_list_item'

COLOR_HEADER = okaara.prompt.COLOR_LIGHT_BLUE
COLOR_IN_PROGRESS = okaara.prompt.COLOR_LIGHT_YELLOW
COLOR_COMPLETED = okaara.prompt.COLOR_LIGHT_GREEN

BAR_PERCENTAGE = .66

# -- classes ------------------------------------------------------------------

class PulpPrompt(Prompt):

    def render_spacer(self, lines=1):
        for i in range(0, lines):
            self.write('')

    def render_title(self, title):

        if self.wrap_width is WIDTH_TERMINAL:
            width = self.terminal_size()[0]
        else:
            width = self.wrap_width

        divider = '+' + ('-' * (width - 2)) + '+'

        self.write(divider)
        self.write(title, center=True, color=COLOR_HEADER, tag=TAG_TITLE)
        self.write(divider)
        self.render_spacer()

    def render_description(self, description):

        self.write(description, tag=TAG_DESCRIPTION)
        self.render_spacer()

    def render_list_of_dict(self, items, filters=None, spaces_between_cols=2):

        # Generate template
        max_key_length = len(max(items, key=len))
        line_template = '%-' + str(max_key_length) + 's:' + (' ' * spaces_between_cols) + '%s'

        # Apply the filters if specified, making sure to not destroy the
        # caller's object in the process
        if filters is not None:
            items = dict([(k, v) for k, v in items if k in filters])

        # Print each item
        for k, v in items:
            line = line_template % (str(k), str(v))
            self.write(line, tag=TAG_MAP_LIST_ITEM)
            self.render_spacer()

        self.render_spacer()

    def create_progress_bar(self, show_trailing_percentage=True):

        if self.wrap_width is WIDTH_TERMINAL:
            width = self.terminal_size()[0]
        else:
            width = self.wrap_width

        width = int(math.floor(BAR_PERCENTAGE * width))

        pb = ProgressBar(self, show_trailing_percentage=show_trailing_percentage,
                         in_progress_color=COLOR_IN_PROGRESS, completed_color=COLOR_COMPLETED)
        return pb

    def create_spinner(self):

        spinner = Spinner(self)
        return spinner

class PulpCli(Cli):
    pass