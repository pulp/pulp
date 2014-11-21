"""
Classes used in the writing of Pulp client extensions.
"""

from gettext import gettext as _
import os

from okaara.cli import (Section, Command, Option, Flag, OptionGroup,
                        OptionValidationFailed, CommandUsage)


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

    def create_option(self, name, description, aliases=None, required=True,
                      allow_multiple=False, default=None, validate_func=None, parse_func=None):
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

        :param validate_func: if specified, this function will be applied to
               the user-specified value
        :type  validate_func: callable

        :param parse_func: if specified, this function will be applied to the
               user-specified value and its return will replace that value
        :type  parse_func: callable

        :return: instance representing the option
        :rtype:  PulpCliOption
        """
        option = PulpCliOption(name, description, required=required, allow_multiple=allow_multiple,
                               aliases=aliases, default=default, validate_func=validate_func,
                               parse_func=parse_func)
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

    def execute(self, prompt, args):

        # Override from Okaara to prevent any non-kwargs from being passed
        # through to the underlying extensions, which have thus far always
        # been told to expect only kwargs. There should be a cleaner way of
        # overriding this in Okaara, but that would require a new build of
        # Okaara and I'm (currently) addressing a CR-2 blocker. Going forward,
        # I'll refactor Okaara and come back here to override the appropriate
        # smaller call. jdob, Sep 4, 2012

        # Parse the command arguments into a dictionary
        try:
            arg_list, kwarg_dict = self.parse_arguments(prompt, args)
        except OptionValidationFailed:
            return os.EX_DATAERR

        # Pulp-specific logic of indicating a problem if there are non-kwargs
        if len(arg_list) > 0:
            raise CommandUsage()

        # Make sure all of the required arguments have been specified. This is
        # different from the Okaara standard version which does not include ''
        # as not fulfilling the required contract. Like the comment above, I'll
        # refactor Okaara to make this easier to override in a subclass so we
        # can remove the bulk of this method from being copied. jdob, Sep 4, 2012
        missing_required = [
            o for o in self.all_options() if o.required and (not kwarg_dict.has_key(o.name)
                                                             or kwarg_dict[o.name] is None
                                                             or kwarg_dict[o.name] == '')]
        if len(missing_required) > 0:
            raise CommandUsage(missing_required)

        # Flag entries that are not specified are parsed as None, but I'd rather
        # them explicitly be set to false. Iterate through each flag explicitly
        # setting the value to false if it was not specified
        for o in self.options:
            if isinstance(o, Flag) and kwarg_dict[o.name] is None:
                kwarg_dict[o.name] = False

        # Clean up option names
        clean_kwargs = dict([(k.lstrip('-'), v) for k, v in kwarg_dict.items()])

        return self.method(*arg_list, **clean_kwargs)

    def print_validation_error(self, prompt, option, exception):
        msg = _('Validation failed for argument [%(name)s]') % {'name': option.name}
        try:
            msg += (': %s' % exception.args[0])
        except (AttributeError, IndexError):
            # Python 2.4 and older does not have an 'args' attribute on Exception.
            # There is also no guarantee that 'args' (an iterable) will have a member.
            pass

        prompt.render_failure_message(msg)


class PulpCliOption(Option):
    pass


class PulpCliFlag(Flag):
    pass


class PulpCliOptionGroup(OptionGroup):
    pass
