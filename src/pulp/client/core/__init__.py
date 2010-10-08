# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
import re
import sys

from pulp.client.logutil import getLogger


_log = getLogger(__name__)
_ignored_modules = ('__init__', 'base', 'utils')
_core_files_regex = re.compile('(?!(%s)).*\.py$' % '|'.join(_ignored_modules))


def _load_module(name):
    """
    Dynamically (re)load a module from disk, given the module name.
    @type name: str
    @param name: name of the module to load
    @rtype: module instance
    @return: loaded module
    """
    # if the module has already been loaded, reload it
    if name in sys.modules:
        del sys.modules[name]
    module = __import__(name, globals(), locals())
    for component in name.split('.')[1:]:
        module = getattr(module, component)
    return module


def _load_core_modules(module_list=None):
    """
    Load the given modules from the core package.
    @type module_list: list or tuple of str's or None
    @param module_list: list of core module names to load, None means load all
    @rtype: dict of str -> module instances
    @return: dictionary of the loaded core modules, keyed by name
    """
    modules = {}
    files = os.listdir(os.path.dirname(__file__))
    for file in filter(_core_files_regex.match, files):
        name = file.split('.', 1)[0]
        if module_list is not None and name not in module_list:
            continue
        module = _load_module('pulp.client.core.' + name)
        modules[name] = module
    return modules


def load_core_commands(command_list=None, actions_dict={}):
    """
    Load the given commands from the core package modules.
    @type command_list: list or tuple of str's or None
    @param command_list: list of core module names to load, None means load all
    @type actions_dict: dict
    @param actions_dict: white list of actions to allow, keyed by command
    @rtype: dict of str -> module instances
    @return: dictionary of the loaded core modules, keyed by name
    """
    assert command_list is None or isinstance(command_list, (list, tuple))
    assert isinstance(actions_dict, dict)
    commands = {}
    # this relies on the commands and modules having the same name
    modules = _load_core_modules(command_list)
    for command, module in modules.items():
        # this relies on the command and the command class having the same name
        if not hasattr(module, 'command_class'):
            _log.error('failed to load command: %s' % command)
            continue
        actions = actions_dict.get(command, None)
        command_class = getattr(module, 'command_class')
        commands[command] = command_class(actions)
    return commands
