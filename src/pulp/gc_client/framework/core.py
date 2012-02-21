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
import sys

from   okaara.cli import Cli
from   okaara.progress import ProgressBar, Spinner
import okaara.prompt
from   okaara.prompt import Prompt, WIDTH_TERMINAL

# -- constants ----------------------------------------------------------------

# Values used for tags in each of the rendering calls; these should be used
# in unit tests to verify the correct write call was made
TAG_TITLE = 'title'
TAG_PARAGRAPH = 'paragraph'
TAG_SECTION = 'section'
TAG_SUCCESS = 'success'
TAG_FAILURE = 'failure'
TAG_EXCEPTION = 'exception'
TAG_DOCUMENT = 'document'
TAG_PROGRESS_BAR = 'progress_bar'
TAG_SPINNER = 'spinner'

COLOR_HEADER = okaara.prompt.COLOR_LIGHT_BLUE
COLOR_SUCCESS = okaara.prompt.COLOR_LIGHT_GREEN
COLOR_FAILURE = okaara.prompt.COLOR_LIGHT_RED
COLOR_IN_PROGRESS = okaara.prompt.COLOR_LIGHT_YELLOW
COLOR_COMPLETED = okaara.prompt.COLOR_LIGHT_GREEN

BAR_PERCENTAGE = .66

# Shadow here so callers don't need to import okaara directly
ABORT = okaara.prompt.ABORT

# -- classes ------------------------------------------------------------------

class PulpPrompt(Prompt):

    ABORT = ABORT

    def __init__(self, input=sys.stdin, output=sys.stdout, enable_color=True,
                 wrap_width=80, record_tags=False):
        Prompt.__init__(self, input=input, output=output, enable_color=enable_color,
                        wrap_width=wrap_width, record_tags=record_tags)

    def render_spacer(self, lines=1):
        """
        Prints the provided number of blank lines.

        :param lines: number of lines to skip
        :type  lines: int
        """
        for i in range(0, lines):
            self.write('')

    def render_title(self, title):
        """
        Prints the given text to the screen, wrapping it in standard Pulp
        formatting for a title.

        A title is meant to be used as the initial text displayed when running
        a command to indicate at a high level what the command did. For example,
        "Repository List" or "Content Types".

        For testing verification, this call will result in one instance of
        TAG_TITLE being recorded.

        :param title: text to format as a title
        :type  title: str
        """

        if self.wrap_width is WIDTH_TERMINAL:
            width = self.terminal_size()[0]
        else:
            width = self.wrap_width

        divider = '+' + ('-' * (width - 2)) + '+'

        self.write(divider)
        self.write(title, center=True, color=COLOR_HEADER, tag=TAG_TITLE)
        self.write(divider)
        self.render_spacer()

    def render_section(self, section):
        """
        Prints the given text to the screen, wrapping it in standard Pulp
        formatting for a section header.

        A section header is meant to be used to separate a large amount of
        output into different sections. The text passed to this call will
        be separated and highlighted to provide a clear break.

        For testing verification, this call will result in one instance of
        TAG_SECTION being recorded.

        :param section: text to format as a paragraph.
        :type  section: str
        """

        self.write(section, tag=TAG_SECTION)
        self.write('-' * len(section))
        self.render_spacer()

    def render_paragraph(self, paragraph):
        """
        Prints the given text to the screen, wrapping it in standard Pulp
        formatting for a description.

        A description is a longer block of arbitrary text to display to the
        user. Multiple paragraphs should be rendered using multiple calls to
        this method instead of concatenting them manually with newline characters.

        For testing verification, this call will result in one instance of
        TAG_PARAGRAPH being recorded.

        :param paragraph: text to format as a paragraph
        :type  paragraph: str
        """

        self.write(paragraph, tag=TAG_PARAGRAPH)
        self.render_spacer()

    def render_success_message(self, message):
        """
        Prints the given text to the screen, wrapping it in standard Pulp
        formatting to indicate an action has successfully taken place.

        :param message: text to format
        :type  message: str
        """

        self.write(message, color=COLOR_SUCCESS, tag=TAG_SUCCESS)
        self.render_spacer()

    def render_failure_message(self, message, reason=None):
        """
        Prints the given text to the screen, wrapping it in standard Pulp
        formatting to indicate an action has failed to complete.

        If a separate reason is provided, it will be displayed in conjunction
        with the failure message.

        :param message: text to format
        :type  message: str

        :param reason: optional text describing why the failure occurred
        :type  reason: str
        """

        self.write(message, color=COLOR_FAILURE, tag=TAG_FAILURE)
        if reason is not None:
            self.write(' - %s' % reason)
        self.render_spacer()

    def render_document(self, document, filters=None, spaces_between_cols=2, indent=0):
        """
        Syntactic sugar method for rendering a single document. This call
        behaves in the same way as render_document_list() but the primary
        argument is a single document (or dict).
        """
        self.render_document_list([document], filters=filters, spaces_between_cols=spaces_between_cols, indent=indent)

    def render_document_list(self, items, filters=None, order=None,
                             spaces_between_cols=2, indent=0):
        """
        Prints a list of JSON documents retrieved from the REST bindings (more
        generally, will print any list of dicts). The data will be output as
        an aligned series of key-value pairs. Keys will be capitalized and all
        unicode markers inserted from the JSON serialization (i.e. u'text')
        will be stripped automatically.

        If filters are specified, only keys in the list of filters will be output.
        Thus the data does not need to be pre-stripped of unwanted fields, this
        call will skip them.

        The order argument is a list of keys in the order theyg should be
        rendered. Any keys not in the given list but that have passed the filter
        test described above will be rendered in alphabetical order following
        the ordered items.

        :param items: list of items (each a dict) to render
        :type  items: list

        :param filters: list of fields in each dict to display
        :type  filters: list

        :param order: list of fields specifying the order in which they are rendered
        :type  order: list

        :param spaces_between_cols: number of spaces between the key and value columns
        :type  spaces_between_cols: int
        """

        # Punch out early if the items list is empty; we access the first
        # element later for max width calculation so we need there to be at
        # least one item.
        if len(items) is 0:
            return

        all_keys = items[0].keys()

        # Generate template
        max_key_length = len(max(all_keys, key=len)) + 1 # +1 for the : appended later
        line_template = (' ' * indent) + '%-' + str(max_key_length) + 's' + (' ' * spaces_between_cols) + '%s'

        # If no filters were specified, consider the filter to be all keys. This
        # will make later calculations a ton easier.
        if filters is None:
            filters = all_keys

        # Apply the filters
        filtered_items = []
        for i in items:
            filtered = dict([(k, v) for k, v in i.items() if k in filters])
            filtered_items.append(filtered)

        # Determine the order to display the items
        if order is None:
            ordered_keys = sorted(filters)
        else:
            # Remove any keys from the order that weren't in the filter
            filtered_order = [o for o in order if o in filters]

            # The order may only be a subset of filtered keys, so figure out
            # which ones are missing and tack them onto the end
            not_ordered = [k for k in filters if k not in filtered_order]

            # Assemble the pieces: ordered keys + not ordered keys
            ordered_keys = order + sorted(not_ordered)

        # Print each item
        for i in filtered_items:
            for k in ordered_keys:
                v = i[k]
                line = line_template % (str(k).capitalize() + ':', str(v))
                self.write(line, tag=TAG_DOCUMENT)
            self.render_spacer()

        self.render_spacer()

    def create_progress_bar(self, show_trailing_percentage=True):
        """
        Creates and configures a progress bar instance. The instance is then
        used to render a progress bar by calling its render() method or
        by wrapping an iterator with its iterator() method prior to iterating
        over it.

        If show_trailing_percentage is set to true, the perentage value will
        be appended at the end of the bar:

        [========================] 100%

        If false, the bar will simply be displayed by itself.

        :type show_trailing_percentage: bool

        :rtype: ProgressBar
        """

        if self.wrap_width is WIDTH_TERMINAL:
            width = self.terminal_size()[0]
        else:
            width = self.wrap_width

        width = int(math.floor(BAR_PERCENTAGE * width))

        pb = ProgressBar(self, width=width, show_trailing_percentage=show_trailing_percentage,
                         in_progress_color=COLOR_IN_PROGRESS, completed_color=COLOR_COMPLETED,
                         render_tag=TAG_PROGRESS_BAR)
        return pb

    def create_spinner(self):
        """
        Creates and configures a spinner instance. A spinner will iterate over
        a series of characters and is intended to show that the client is
        performing work on an unbounded number of items. The next item in
        the spinners enumerated set of values is displayed by calling it's
        spin() method.

        :rtype: Spinner
        """

        spinner = Spinner(self, spin_tag=TAG_SPINNER)
        return spinner

class PulpCli(Cli):
    pass