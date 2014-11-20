# -*- coding: utf-8 -*-

"""
Functionality related to loading extensions from a set location. The client
context is constructed ahead of time and provided to this module, which
then uses it to instantiate the extension components.
"""

import copy
from gettext import gettext as _
import logging
import os
import sys

import pkg_resources


_logger = logging.getLogger(__name__)


# Names of the modules in each extension pack for initializing the pack
_MODULE_CLI = 'pulp_cli'
_MODULE_SHELL = 'pulp_shell'

PRIORITY_VAR = 'PRIORITY'
DEFAULT_PRIORITY = 5

_MODULES = 'modules'
_ENTRY_POINTS = 'entry points'
# name of the entry point
ENTRY_POINT_EXTENSIONS = 'pulp.extensions.%s'


class ExtensionLoaderException(Exception):
    """ Base class for all loading-related exceptions. """
    pass


class InvalidExtensionsDirectory(ExtensionLoaderException):
    def __init__(self, dir):
        ExtensionLoaderException.__init__(self)
        self.dir = dir

    def __str__(self):
        return _('Inaccessible or missing extensions directory [%(d)s]' % {'d': self.dir})


class LoadFailed(ExtensionLoaderException):
    """
    Raised if one or more of the extensions failed to load. All failed
    extensions will be listed in the exception, however the causes are logged
    rather than carried in this exception.
    """

    def __init__(self, failed_packs):
        ExtensionLoaderException.__init__(self)
        self.failed_packs = failed_packs

    def __str__(self):
        return _(
            'The following extension packs failed to load: [%s]' % ', '.join(self.failed_packs))


# Unit test marker exceptions
class ImportFailed(ExtensionLoaderException):
    def __init__(self, pack_name):
        ExtensionLoaderException.__init__(self)
        self.pack_name = pack_name


class NoInitFunction(ExtensionLoaderException):
    pass


class InitError(ExtensionLoaderException):
    pass


class InvalidExtensionConfig(ExtensionLoaderException):
    pass


def load_extensions(extensions_dir, context, role):
    """
    @param extensions_dir: directory in which to find extension packs
    @type  extensions_dir: str

    The "sorted_extensions" data structure is a dict whose keys are priorities.
    Each value in the dict is a new dict in this form:
    { _MODULES : [<list of modules>], _ENTRY_POINTS : [<list of entry points>]}
    This way we can load the modules and entry points for a given priority at
    the same time.

    @param context: pre-populated context the extensions should be given to
                    interact with the client
    @type  context: pulp.client.extensions.core.ClientContext

    @param role:    name of a role, either "admin" or "consumer", so we know
                    which extensions to load
    @type  role:    str
    """

    # Validation
    if not os.access(extensions_dir, os.F_OK | os.R_OK):
        raise InvalidExtensionsDirectory(extensions_dir)

    # identify modules and sort them
    try:
        unsorted_modules = _load_pack_modules(extensions_dir)
        sorted_extensions = _resolve_order(unsorted_modules)
    except ImportFailed, e:
        raise LoadFailed([e.pack_name]), None, sys.exc_info()[2]

    # find extensions from entry points and add them to the sorted structure
    for extension in pkg_resources.iter_entry_points(ENTRY_POINT_EXTENSIONS % role):
        priority = getattr(extension, PRIORITY_VAR, DEFAULT_PRIORITY)
        sorted_extensions.setdefault(priority, {}).setdefault(_ENTRY_POINTS, []).append(extension)

    error_packs = []
    for priority in sorted(sorted_extensions.keys()):
        for module in sorted_extensions[priority].get(_MODULES, []):
            try:
                _load_pack(extensions_dir, module, context)
            except ExtensionLoaderException, e:
                # Do a best-effort attempt to load all extensions. If any fail,
                # the cause will be logged by _load_pack. This method should
                # continue to load extensions so all of the errors are logged.
                error_packs.append(module.__name__)
        for entry_point in sorted_extensions[priority].get(_ENTRY_POINTS, []):
            entry_point.load()(context)

    if len(error_packs) > 0:
        raise LoadFailed(error_packs)


def _load_pack_modules(extensions_dir):
    """
    Loads the modules for each pack in the extensions directory, taking care
    to update the system path as appropriate.

    @return: list of module instances loaded from the call
    @rtype:  list

    @raises ImportFailed: if any of the entries in extensions_dir cannot be
            loaded as a python module
    """

    # Add the extensions directory to the path so each extension can be
    # loaded as a python module
    if extensions_dir not in sys.path:
        sys.path.append(extensions_dir)

    modules = []

    pack_names = sorted(os.listdir(extensions_dir))
    for pack in pack_names:
        if pack.startswith('.'):
            continue
        try:
            mod = __import__(pack)
            modules.append(mod)
        except Exception, e:
            raise ImportFailed(pack), None, sys.exc_info()[2]

    return modules


def _resolve_order(modules):
    """
    Determines the order in which the given modules should be initialized. The
    determination is made by inspecting the module's init script for the
    presence of the priority value. If none is specified, it is defaulted.
    See the constants in this module for the actual values of both of these.

    This method makes no assumptions on the valid range of priorities. Lower
    priorities will be loaded before higher priorities.

    @param modules: list of extension module instances
    @type  modules: list

    @return: dict where keys are priority levels, and values are dicts with key
             = _MODULES and value = list of modules
    @rtype:  dict
    """

    # Split apart the modules by priority first
    modules_by_priority = {}  # key: priority, value: module

    for m in modules:
        try:
            m_priority = int(getattr(m, PRIORITY_VAR))
        except AttributeError, e:
            # Priority is optional; the default is applied here
            m_priority = DEFAULT_PRIORITY

        priority_level = modules_by_priority.setdefault(m_priority, {})
        priority_mods = priority_level.setdefault(_MODULES, [])
        priority_mods.append(m)

    # Within each priority, sort each module alphabetically by name
    for priority in modules_by_priority.keys():
        priority_modules = modules_by_priority[priority].get(_MODULES, [])
        priority_modules.sort(key=lambda x: x.__name__)

    return modules_by_priority


def _load_pack(extensions_dir, pack_module, context):
    # Figure out which initialization module we're loading
    init_mod_name = None
    if context.cli is not None:
        init_mod_name = _MODULE_CLI
    elif context.shell is not None:
        init_mod_name = _MODULE_SHELL

    # Check for the file's existence first. This will make it easier to
    # differentiate the difference between a pack not supporting a particular
    # UI style and a failure to load the init module.
    init_mod_filename = os.path.join(extensions_dir, pack_module.__name__, init_mod_name + '.py')
    if not os.path.exists(init_mod_filename):
        _logger.debug(_('No plugin initialization module [%(m)s] found, skipping '
                        'initialization' % {'m': init_mod_filename}))
        return

    # Figure out the full package name for the module and import it.
    try:
        init_mod = __import__('%s.%s' % (pack_module.__name__, init_mod_name))
    except Exception, e:
        _logger.exception(_('Could not load initialization module [%(m)s]' % {'m': init_mod_name}))
        raise ImportFailed(pack_module.__name__), None, sys.exc_info()[2]

    # Get a handle on the initialize function
    try:
        ui_init_module = getattr(init_mod, init_mod_name)
        init_func = getattr(ui_init_module, 'initialize')
    except AttributeError, e:
        _logger.exception(_('Module [%(m)s] does not define the required '
                            'initialize function' % {'m': init_mod_name}))
        raise NoInitFunction(), None, sys.exc_info()[2]

    # Invoke the module's initialization, passing a copy of the context so
    # one extension doesn't accidentally muck with it and affect another.
    context_copy = copy.copy(context)
    context_copy.config = copy.copy(context.config)

    try:
        init_func(context_copy)
    except Exception, e:
        _logger.exception(_('Module [%(m)s] could not be initialized' % {'m': init_mod_name}))
        raise InitError(), None, sys.exc_info()[2]
