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
Classes used in the writing of Pulp client extensions.
"""

from gettext import gettext as _

from okaara.cli import Section, Command, Option, Flag, OptionGroup
from okaara.cli import UnknownArgsParser # shadow here so extensions can import it from this module

# -- cli components -----------------------------------------------------------

class PulpCliSection(Section):

    def create_command(self, name, description, method, usage_description=None, parser=None):
        """
        Creates a new command in this section. The given name must be
        unique across all commands and subsections within this section.
        The command instance is returned and can be further edited except
        for its name.

        Commands created in this fashion do not need to be added to this
        section through the add_command method.

        :param name: trigger that will cause this command to run
        :type  name: str

        :param description: user-readable text describing what happens when
               running this command; displayed to users in the usage output
        :type  description: str

        :param method: method that will be invoked when this command is run
        :type  method: function

        :param parser: if specified, the remaining arguments to this command
               as specified by the user will be passed to this object to
               be handled; the results will be sent to the command's method
        :type  parser: OptionParser

        :return: instance representing the newly added command
        :rtype:  PulpCliCommand
        """
        command = PulpCliCommand(name, description, method, parser=parser)
        self.add_command(command)
        return command

    def create_subsection(self, name, description):
        """
        Creates a new subsection in this section. The given name must be unique
        across all commands and subsections within this section. The section
        instance is returned and can be further edited except for its name.

        Sections created in this fashion do not need to be added to this section
        through the add_section method.

        :param name: identifies the section
        :type  name: str

        :param description: user-readable text describing the contents of this
               subsection
        :type  description: str

        :return: instance representing the newly added section
        :rtype:  PulpCliSection
        """
        subsection = PulpCliSection(name, description)
        self.add_subsection(subsection)
        return subsection


class PulpCliCommand(Command):

    REQUIRED_OPTION_PREFIX = _('(required) ')
    OPTIONAL_OPTION_PREFIX = ''

    def create_option(self, name, description, aliases=None, required=True, allow_multiple=False, default=None):
        """
        Creates a new option for this command. An option is an argument to the
        command line call that accepts a value.

        The given name must be unique across all options within this command.
        The option instance is returned and can be further edited except for
        its name.

        If the default parser is used by the command, the name must match the
        typical command line argument format, either:

        * -s - where s is a single character
        * --detail - where the argument is longer than one character

        The default parser will strip off the leading hyphens when it makes the
        values available to the command's method.

        :param name: trigger to set the option
        :type  name: str

        :param description: user-readable text describing what the option does
        :type  description: str

        :param aliases: list of other argument names that may be used to set
               the value for this option
        :type  aliases: list

        :param required: if true, the default parser will enforce the the user
               specifies this option and display a usage warning otherwise
        :type  required: bool

        :param allow_multiple: if true, the value of this option when parsed
               will be a list of values in the order in which the user entered them
        :type  allow_multiple: bool
        
        :param default: The default value for optional options
        :type  default: object

        :return: instance representing the option
        :rtype:  PulpCliOption
        """
        option = PulpCliOption(name, description, required=required, allow_multiple=allow_multiple, aliases=aliases, default=default)
        self.add_option(option)
        return option

    def create_flag(self, name, description, aliases=None):
        """
        Creates a new flag for this command. A flag is an argument that accepts
        no value from the user. If specified, the value will be True when it
        is passed to the command's underlying method. Flags are, by their
        nature, always optional.

        The given name must be unique across all options within this command.
        The option instance is returned and can be further edited except for
        its name.

        If the default parser is used by the command, the name must match the
        typical command line argument format, either:

        * -s - where s is a single character
        * --detail - where the argument is longer than one character

        The default parser will strip off the leading hyphens when it makes the
        values available to the command's method.

        :param name: trigger to set the flag
        :type  name: str

        :param description: user-readable text describing what the option does
        :type  description: str

        :param aliases: list of other argument names that may be used to set
               the value for this flag
        :type  aliases: list

        :return: instance representing the flag
        :rtype:  PulpFliFlag
        """
        flag = PulpCliFlag(name, description, aliases=aliases)
        self.add_option(flag)
        return flag

class PulpCliOption(Option):
    pass

class PulpCliFlag(Flag):
    pass

class PulpCliOptionGroup(OptionGroup):
    pass