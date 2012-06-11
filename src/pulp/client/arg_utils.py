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
Utilities for enforcing and parsing command line argument conventions.
"""

from gettext import gettext as _

class InvalidConfig(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass

def convert_removed_options(args):
    """
    Applies the convention for removing configuration options through the CLI.
    The convention is to specify the value as missing or simply "". For
    example:

    --foo=
      or
    --foo=""

    This method is intended to be run on the kwargs dict given to the method
    after the framework parses the user arguments. This call will do the
    following:

    * Remove any keys whose value is None. The way the framework parser works,
      expected options that the user did not specify have a value of None.
      We don't want to send those as they don't represent user input.
    * Convert any keys whose value was "" into None. This represents the case
      that the user is explicitly removing the value for the option.

    This call will modify the specified args dict in place.

    @param args: key-value pairs to apply removal conventions on.
    @type  args: dict
    """

    # Strip out anything with a None value. The way the parser works, all of
    # the possible options will be present with None as the value. Strip out
    # everything with a None value now as it means it hasn't been specified
    # by the user (removals are done by specifying ''.
    for k, v in args.items():
        if v is None:
            args.pop(k)

    # Now convert any "" strings into None. This should be safe in all cases and
    # is the mechanic used to get "remove config option" semantics.
    convert_keys = [k for k in args if args[k] == '']
    for k in convert_keys:
        args[k] = None

def convert_boolean_arguments(boolean_keys, args):
    """
    For each given key, if it is in the args dict this call will attempt to convert
    the user-provided text for true/false into an actual boolean. The boolean
    value is stored directly into args and replaces the text version. If the
    key is not present or is None, this method does nothing for that key. If the
    value for a key isn't parsable into a boolean, an InvalidConfig exception
    is raised with a pre-formatted message indicating such.

    This call will modify the specified args dict in place.

    @param boolean_keys: list of keys to convert in the given config
    @type  boolean_keys: list or tuple

    @param args: key-value pairs to convert; may include keys not indicated in
                 boolean_keys
    @type  args: dict

    @raise InvalidConfig: if the value for a supposed boolean key is not parsable
    """

    for key in boolean_keys:
        if key not in args or args[key] is None:
            continue
        convert_me = args.pop(key)
        converted = arg_to_bool(convert_me)

        if converted is not None:
            args[key] = converted
        else:
            raise InvalidConfig(_('Value for %(f)s must be either true or false' % {'f' : key}))

def arg_to_bool(arg_value):
    """
    Applies the CLI convention for accepting text representations for booleans
    and returns the boolean equivalent. If the value does not match the
    convention, None is returned. The expectation is that the caller will check
    for None and display an appropriate error message.

    @param arg_value: value to parse
    @type  arg_value: str

    @return: boolean equivalent of the user-entered string; None if it cannot
             be parsed
    @rtype:  bool
    """

    if arg_value.strip().lower() == 'true':
        return True
    if arg_value.strip().lower() == 'false':
        return False

    return None

def convert_file_contents(file_keys, args):
    """
    For each given key, if it is in the args dict this call will attempt to read
    the file indicated by the key value. The contents of the file are stored
    directly into args and replaces the filename itself. If the key is not
    present or is None, this method does nothing for that key. If the value for
    the key cannot be read in as a file, an InvalidConfig exception is raised
    with a pre-formatted message indicating such.

    This call will modify the specified args dict in place.

    @param file_keys: list of keys to read in as files
    @type  file_keys: list or tuple

    @param args: key-value pairs to convert; may include keys not indicated in
                 file_keys
    @type  args: dict

    @raise InvalidConfig: if the contents of a file key cannot be read
    """

    for key in file_keys:
        if key in args and args[key] is not None:
            filename = args[key]
            try:
                f = open(filename)
                contents = f.read()
                f.close()

                args[key] = contents
            except:
                raise InvalidConfig(_('File [%(f)s] cannot be read' % {'f' : filename}))

