#!/usr/bin/python
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
This module copied from the okaara project:
  https://github.com/jdob/okaara
"""

import getpass
import logging
import os
import sys

# -- constants ----------------------------------------------------------------

LOG = logging.getLogger(__name__)

# Returned to indicate the user has interrupted the input
ABORT = object()

COLOR_WHITE = '\033[0m'
COLOR_BRIGHT_WHITE = '\033[1m'

COLOR_GRAY = '\033[30m'
COLOR_RED = '\033[31m'
COLOR_GREEN = '\033[32m'
COLOR_YELLOW = '\033[33m'
COLOR_BLUE = '\033[34m'
COLOR_PURPLE = '\033[35m'
COLOR_CYAN = '\033[36m'

COLOR_LIGHT_GRAY = '\033[90m'
COLOR_LIGHT_RED = '\033[91m'
COLOR_LIGHT_GREEN = '\033[92m'
COLOR_LIGHT_YELLOW = '\033[93m'
COLOR_LIGHT_BLUE = '\033[94m'
COLOR_LIGHT_PURPLE = '\033[95m'
COLOR_LIGHT_CYAN = '\033[96m'

COLOR_BG_GRAY = '\033[40m'
COLOR_BG_RED = '\033[41m'
COLOR_BG_GREEN = '\033[42m'
COLOR_BG_YELLOW = '\033[43m'
COLOR_BG_BLUE = '\033[44m'
COLOR_BG_PURPLE = '\033[45m'
COLOR_BG_CYAN = '\033[46m'

POSITION_SAVE = '\033[s'
POSITION_RESET = '\033[u'

MOVE_UP = '\033[%dA' # sub in number of lines
MOVE_DOWN = '\033[%dB' # sub in number of lines
MOVE_FORWARD = '\033[%dC' # sub in number of characters
MOVE_BACKWARD = '\033[%dD' # sub in number of characters

CLEAR = '\033[2J'
CLEAR_EOL = '\033[K'

# -- classes ------------------------------------------------------------------

class Terminal:

    def __init__(self, input=sys.stdin, output=sys.stdout, normal_color=COLOR_WHITE,
                 enable_color=True, wrap_width=None):
        """
        Creates a new instance that will read and write to the given streams.

        @param input: stream to read from; defaults to stdin
        @type  input: file

        @param output: stream to write prompt statements to; defaults to stdout
        @type  output: file

        @param normal_color: color of the text to write; this will be used in the color
                             function to reset the text after coloring it
        @type  normal_color: str (one of the COLOR_* variables in this module)

        @param enable_color: determines if this prompt instance will output any modified
                             colors; if this is false the color() method will
                             always render the text as the normal_color
        @type  enable_color: bool

        @param wrap_width: if specified, content written by this prompt will
                           automatically be wrapped to this width
        @type  wrap_width: int or None
        """
        self.input = input
        self.output = output
        self.normal_color = normal_color
        self.enable_color = enable_color
        self.wrap_width = wrap_width

        # Initialize the screen with the normal color
        self.write(self.normal_color, new_line=False)

    def read(self, prompt):
        """
        Reads user input. This will likely not be called in favor of one of the prompt_* methods.

        @param prompt: the prompt displayed to the user when the input is requested
        @type  prompt: string

        @return: the input specified by the user
        @rtype:  string
        """
        self.write(prompt, new_line=False)
        return self.input.readline().rstrip() # rstrip removes the trailing \n

    def write(self, content, new_line=True):
        """
        Writes content to the prompt's output stream.

        @param content: content to display to the user
        @type  content: string
        """
        content = self._chop(content, self.wrap_width)

        if new_line: content += '\n'

        self.output.write(content)

    def color(self, text, color):
        """
        Colors the given text with the given color, resetting the output back to whatever
        color is defined in this instance's normal_color. Nothing is output to the screen;
        the formatted string is returned.

        @param text: text to color
        @type  text: str

        @param color: coding for the color (see the COLOR_* variables in this module)
        @type  color: str

        @return: new string with the proper color escape sequences in place
        @rtype:  str
        """

        # Handle if color is disabled at the instance level
        if not self.enable_color:
            color = self.normal_color

        return color + text + self.normal_color

    def center(self, text, width=None):
        """
        Centers the given text. Nothing is output to the screen; the formatted string
        is returned.

        @param text: text to center
        @type  text: str

        @param width: width to center the text between; if None the wrap_width value
                      will be used
        @type  width: int
        """

        if width is None:
            width = self.wrap_width

        if len(text) >= width:
            return text
        else:
            spacer = ' ' * ( (width - len(text)) / 2)
            return spacer + text

    def clear(self):
        """
        Clears the screen.
        """
        self.write(CLEAR, new_line=False)

    def _chop(self, content, wrap_width):
        """
        If the wrap_width is specified, this call will introduce \n characters
        to maintain that width.
        """
        if wrap_width is None:
            return content

        wrapped_content = ''
        remainder = content[:]
        while True:
            chopped = remainder[:wrap_width]
            remainder = remainder[wrap_width:]

            wrapped_content += chopped

            if len(remainder) is 0:
                return wrapped_content
            else:
                wrapped_content += '\n'


class Prompt(Terminal):
    """
    Used to communicate between the application and the user. The Prompt class can be
    subclassed to provide custom implementations of read and write to alter the input/output
    sources. By default, stdin and stdout will be used.
    """

    # -- prompts --------------------------------------------------------------

    def prompt_file(self, question, allow_directory=False, allow_empty=False, interruptable=True):
        """
        Prompts the user for the full path to a file, reprompting if the file does not
        exist. If allow_empty is specified, the validation will only be performed if the
        user enters a value.
        """
        f = self.prompt(question, allow_empty=allow_empty, interruptable=interruptable)

        if (f is None or f.strip() == '') and allow_empty:
            return f
        elif os.path.exists(f) and (allow_directory or os.path.isfile(f)):
            return f
        else:
            self.write('Cannot find file, please enter a valid path')
            self.write('')
            return self.prompt_file(question)

    def prompt_values(self, question, values, interruptable=True):
        """
        Prompts the user for the answer to a question where only an enumerated set of values
        should be accepted.

        @param values: list of acceptable answers to the question
        @type  values: list

        @return: will be one of the entries in the values parameter
        @rtype:  string
        """
        a = None
        while a not in values:
            a = self.prompt(question, interruptable=interruptable)

        return a

    def prompt_y_n(self, question, interruptable=True):
        """
        Prompts the user for the answer to a yes/no question, assuming the value 'y' for yes and
        'n' for no. If neither is entered, the user will be re-prompted until one of the two is
        indicated.

        @return: True if 'y' was specified, False otherwise
        @rtype:  boolean
        """
        a = ''
        while a != 'y' and a != 'n' and a is not ABORT:
            a = self.prompt(question, interruptable=interruptable)

        if a is ABORT:
            return a
            
        return a.lower() == 'y'

    def prompt_range(self, question, high_number, low_number=1, interruptable=True):
        """
        Prompts the user to enter a number between the given range. If the input is invalid, the
        user wil be re-prompted until a valid number is provided.
        """
        while True:
            a = self.prompt_number(question, interruptable=interruptable)

            if a > high_number or a < low_number:
                self.write('Please enter a number between %d and %d' % (low_number, high_number))
                continue
                
            return a

    def prompt_number(self, question, allow_negatives=False, allow_zero=False, default_value=None, interruptable=True):
        """
        Prompts the user for a numerical input. If the given value does not represent a number,
        the user will be re-prompted until a valid number is provided.

        @return: number entered by the user that conforms to the parameters in this call
        @rtype:  int
        """
        while True:
            a = self.prompt(question, allow_empty=default_value is not None, interruptable=interruptable)

            if (a is None or a == '') and default_value is not None:
                return default_value
            
            if not a.isdigit():
                self.write('Please enter a number')
                continue

            i = int(a)

            if not allow_negatives and i < 0:
                self.write('Please enter a number greater than zero')
                continue

            if not allow_zero and i == 0:
                self.write('Please enter a non-zero value')
                continue

            return i

    def prompt_default(self, question, default_value, interruptable=True):
        """
        Prompts the user for an answer to the given question. If the user does not enter a value,
        the default will be returned.

        @param default_value: if the user does not enter a value, this value is returned
        @type  default_value: string
        """
        answer = self.prompt(question, allow_empty=True, interruptable=interruptable)

        if answer is None or answer == '':
            return default_value
        else:
            return answer

    def prompt_multiselect_menu(self, question, menu_values, interruptable=True):
        """
        Displays a list of items, allowing the user to select 1 or more items before continuing.
        The items selected by the user are returned.

        @return: list of indices of the items the user selected, empty list if none are selected;
                 None is returned if the user selects to abort the menu
        @rtype : list of int or None
        """
        selected_indices = []

        q = 'Enter value (1-%s) to toggle selection, \'c\' to confirm selections, or \'?\' for more commands: ' % len(menu_values)

        while True:
            self.write(question)

            # Print the current state of the list
            for index, value in enumerate(menu_values):

                if index in selected_indices:
                    is_selected = 'x'
                else:
                    is_selected = '-'

                self.write('  %s  %-2d: %s' % (is_selected, index + 1, value))

            selection = self.prompt(q, interruptable=interruptable)
            self.write('')

            if selection is ABORT:
                return ABORT
            elif selection == '?':
                self.write('  <num> : toggles selection, value values between 1 and %s' % len(menu_values))
                self.write('  x-y  : toggle the selection of a range of items (example: "2-5" toggles items 2 through 5)')
                self.write('  a    : select all items')
                self.write('  n    : select no items')
                self.write('  c    : confirm the currently selected items')
                self.write('  b    : abort the item selection')
                self.write('  l    : clears the screen and redraws the menu')
                self.write('')
            elif selection == 'c':
                return selected_indices
            elif selection == 'a':
                selected_indices = range(0, len(menu_values))
            elif selection == 'n':
                selected_indices = []
            elif selection == 'b':
                return ABORT
            elif selection == 'l':
                self.clear()
            elif self._is_range(selection, len(menu_values)):
                lower, upper = self._range(selection)
                for i in range(lower, upper + 1):
                    if i in selected_indices:
                        selected_indices.remove(i)
                    else:
                        selected_indices.append(i)
            elif selection.isdigit() and int(selection) < (len(menu_values) + 1):
                value_index = int(selection) - 1

                if value_index in selected_indices:
                    selected_indices.remove(value_index)
                else:
                    selected_indices.append(value_index)

    def prompt_multiselect_sectioned_menu(self, question, section_items, section_post_text=None, interruptable=True):
        """
        Displays a multiselect menu for the user where the items are broken up by section,
        however the numbering is consecutive to provide unique indices for the user to use
        for selection. Entries from one or more section may be toggled; the section
        headers are merely used for display purposes.

        Each key in section_items is displayed as the section header. Each item in the
        list at that key will be rendered as belonging to that section.

        The returned value will be a dict that maps each section header (i.e. key in section_items)
        and the value is a list of indices that were selected from the original list passed in
        section_items under that key. If no items were selected under a given section, an empty
        list is the value in the return for each section key.

        For example, given the input data:
        { 'Section 1' : ['Item 1.1', 'Item 1.2'],
          'Section 2' : ['Item 2.1'],
        }

        The following is rendered for the user:
             Section 1
                -  1 : Item 1.1
                -  2 : Item 1.2
              Section 2
                -  3 : Item 2.1

        If the user entered 1, 2, and 3, thus toggling them as selected, the following would be returned:
        { 'Section 1' : [0, 1],
          'Section 2' : [0],
        }

        However, if only 2 was toggled, the return would be:
        { 'Section 1' : [1],
          'Section 2' : [],
        }

        If the user chooses the "abort" option, None is returned.

        @param question: displayed to the user before displaying the menu
        @type  question: str

        @param section_items: data to be rendered; each key must be a string and each value must
                              be a list of strings
        @type  section_items: dict {str : list[str]}

        @param section_post_text: if specified, this string will be displayed on its own line between
                                  each section
        @type  section_post_text: str

        @return: selected indices for each list specified in each section; see above
        @rtype:  dict {str : list[int]}
        """
        selected_index_map = {}
        for key in section_items:
            selected_index_map[key] = []

        total_item_count = reduce(lambda count, key: count + len(section_items[key]), section_items.keys(), 0)

        q = 'Enter value (1-%s) to toggle selection, \'c\' to confirm selections, or \'?\' for more commands: ' % total_item_count

        while True:
            self.write(question)

            # Print current state of the list, keeping a running tuple that maps the index
            # displayed to/used by the user to the section key and index that item was found in
            mapper = []
            counter = 1

            for key in section_items:

                # Write the section header
                self.write('  %s' % key)

                # Render the list, using an incrementing toggle number that transcends any one section
                for index, item in enumerate(section_items[key]):
                    if index in selected_index_map[key]:
                        is_selected = 'x'
                    else:
                        is_selected = '-'

                    self.write('    %s  %-2d: %s' % (is_selected, counter, item))
                    mapper.append((key, index))
                    counter += 1

                # If the caller wants something between sections, display it now
                if section_post_text is not None:
                    self.write(section_post_text)

            selection = self.prompt(q, interruptable=interruptable)
            self.write('')

            if selection is ABORT:
                return ABORT
            elif selection == '?':
                self.write('  <num> : toggles selection, value values between 1 and %s' % total_item_count)
                self.write('  x-y   : toggle the selection of a range of items (example: "2-5" toggles items 2 through 5)')
                self.write('  a     : select all items')
                self.write('  n     : select no items')
                self.write('  c     : confirm the currently selected items')
                self.write('  b     : abort the item selection')
                self.write('  l     : clears the screen and redraws the menu')
                self.write('')
            elif selection == 'c':
                return selected_index_map
            elif selection == 'a':
                # Recreate the selected index map, adding in indices for each item
                selected_index_map = {}
                for key in section_items:
                    selected_index_map[key] = range(0, len(section_items[key]))
            elif selection == 'n':
                selected_index_map = {}
                for key in section_items:
                    selected_index_map[key] = []
            elif selection == 'b':
                return ABORT
            elif selection == 'l':
                self.clear()
            elif self._is_range(selection, total_item_count):
                lower, upper = self._range(selection)
                for i in range(lower, upper + 1):
                    section_key = mapper[i][0]
                    section_index = mapper[i][1]

                    if section_index in selected_index_map[section_key]:
                        selected_index_map[section_key].remove(section_index)
                    else:
                        selected_index_map[section_key].append(section_index)
            elif selection.isdigit() and int(selection) < (total_item_count + 1):
                value_index = int(selection) - 1
                section_key = mapper[value_index][0]
                section_index = mapper[value_index][1]

                if section_index in selected_index_map[section_key]:
                    selected_index_map[section_key].remove(section_index)
                else:
                    selected_index_map[section_key].append(section_index)

    def prompt_menu(self, question, menu_values, interruptable=True):
        """
        Displays a list of items, allowing the user to select a single item in the
        list. The selected value is returned.

        @param question: displayed to the user prior to rendering the list
        @type  question: str

        @param menu_values: list of items to display in the menu; the returned value
                            will be one of the items in this list
        @type  menu_values: list of str

        @return: index of the selected item; None if the user elected to abort
        @rtype:  int or None
        """

        self.write(question)

        for index, value in enumerate(menu_values):
            self.write('  %-2d - %s' % (index + 1, value))

        q = 'Enter value (1-%d) or \'b\' to abort: ' % len(menu_values)

        while True:
            selection = self.prompt(q, interruptable=interruptable)

            if selection is ABORT or selection == 'b':
                return ABORT
            elif selection.isdigit() and int(selection) < (len(menu_values) + 1):
                return int(selection) - 1 # to remove the +1 for display purposes

    def prompt_password(self, question, verify_question=None, unmatch_msg=None):
        """
        Prompts the user for a password. If a verify question is specified, the
        user will be prompted to match the previously entered password (suitable
        for things such as changing a password). If it is not specified, the first
        value entered will be returned.

        The user entered text will not be echoed to the screen.

        Due to the way getpass works, this method intentionally does not support
        the "interruptable" keyword.

        @return: entered password
        @rtype:  str
        """
        while True:
            password_1 = getpass.getpass(question, stream=self.output)

            if verify_question is None:
                return password_1

            password_2 = getpass.getpass(verify_question, stream=self.output)

            if password_1 != password_2:
                self.write(unmatch_msg)
                self.write('')
            else:
                return password_1

    def prompt(self, question, allow_empty=False, interruptable=True):
        """
        Prompts the user for an answer to the given question, re-prompting if the answer is
        blank.

        @param question: displayed to the user when prompting for input
        @type  question: str

        @param allow_empty: if True, a blank line will be accepted as input
        @type  allow_empty: bool

        @param interruptable: if True, keyboard interrupts will be caught and None will
                              be returned; if False, keyboard interrupts will raise as
                              normal
        @type  interruptable: bool

        @return: answer to the given question or ABORT if it was interrupted
        """
        answer = None
        while answer is None or answer.strip() == '':

            try:
                answer = self.read(question)
                if allow_empty: break
            except (EOFError, KeyboardInterrupt), e:
                if interruptable:
                    return ABORT
                else:
                    raise e

        return answer

    # -- utilities ------------------------------------------------------------

    def _is_range(self, input, selectable_item_count):
        """
        @return: True if the input represents a range in a multiselect menu,
                 False otherwise
        @rtype:  bool
        """
        parsed = input.split('-')
        if len(parsed) != 2:
            return False

        lower = parsed[0].strip()
        upper = parsed[1].strip()

        return lower.isdigit() and int(lower) > 0 and \
               upper.isdigit() and int(upper) <= selectable_item_count and \
               int(lower) < int(upper)

    def _range(self, input):
        """
        If an input is determined to be a range by _is_range, this call will
        return the lower and upper indices of the range (the entered values
        will be subtracted by 1 to accomodate for UI view).

        @return: tuple of (lower boundary, upper boundary)
        @rtype: (int, int)
        """
        parsed = input.split('-')
        return int(parsed[0].strip()) - 1, int(parsed[1].strip()) - 1


class ScriptedPrompt(Prompt):
    """
    Prompt subclass that returns user input from a pre-set list of strings. Output will
    be written to a separate list of strings, allowing non-interactive alternatives for
    working with a prompt.
    """

    def __init__(self):
        """
        Initializes with an empty list of return prompt read results.
        """
        Prompt.__init__(self)

        self.read_values = []
        self.write_values = []

    def read(self, prompt):
        """
        Returns the next item in the script list as the result.
        """
        return self.read_values.pop(0)

    def write(self, content, new_line=True):
        """
        Stores the written message to the internal cache.
        """
        self.write_values.append(content)
