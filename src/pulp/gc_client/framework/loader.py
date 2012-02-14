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
Functionality related to loading extensions from a set location. The client
context is constructed ahead of time and provided to this module, which
then uses it to instantiate the extension components.
"""

import copy
from gettext import gettext as _
import logging
import os
import sys

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# Names of the modules in each extension pack for initializing the pack
_MODULE_CLI = 'pulp_cli'
_MODULE_SHELL = 'pulp_shell'

# -- exceptions ---------------------------------------------------------------

class ExtensionLoaderException(Exception):
    """ Base class for all loading-related exceptions. """
    pass

class InvalidExtensionsDirectory(ExtensionLoaderException):
    def __init__(self, dir):
        super(InvalidExtensionsDirectory, self).__init__()
        self.dir = dir

    def __str__(self):
        return _('Inaccessible or missing extensions directory [%(d)s]' % {'d' : self.dir})

# Unit test marker exceptions
class NoInitModule(ExtensionLoaderException): pass
class ImportFailed(ExtensionLoaderException): pass
class NoInitFunction(ExtensionLoaderException): pass
class InitError(ExtensionLoaderException): pass

# -- loading ------------------------------------------------------------------

def load_extensions(extensions_dir, context):
    """
    @param extensions_dir: directory in which to find extension packs
    @type  extensions_dir: str

    @param context: pre-populated context the extensions should be given to
                    interact with the client
    @type  context: ClientContext
    """

    # Validation
    if not os.access(extensions_dir, os.F_OK | os.R_OK):
        raise InvalidExtensionsDirectory(extensions_dir)

    # Add the extensions directory to the path so each extension can be
    # loaded as a python module
    if extensions_dir not in sys.path:
        sys.path.append(extensions_dir)

    # Handle each extension pack in the directory in alphabetical order so
    # we can guarantee the loading order
    pack_names = sorted(os.listdir(extensions_dir))
    for pack in pack_names:
        try:
            _load_pack(extensions_dir, pack, context)
        except ExtensionLoaderException:
            # Do a best-effort attempt to load all extensions. If any fail,
            # the cause will be logged by _load_pack. This method should
            # continue to load extensions and thus the pass below is intentional.
            pass

def _load_pack(extensions_dir, pack_name, context):

    # Figure out which initialization module we're loading
    init_mod_name = None
    if context.cli is not None:
        init_mod_name = _MODULE_CLI
    elif context.shell is not None:
        init_mod_name = _MODULE_SHELL

    # Check for the file's existence first. This will make it easier to
    # differentiate the difference between a pack not supporting a particular
    # UI style and a failure to load the init module.
    init_mod_filename = os.path.join(extensions_dir, pack_name, init_mod_name + '.py')
    if not os.path.exists(init_mod_filename):
        _LOG.info(_('No initialization module [%(m)s] found, skipping initialization' % {'m' : init_mod_filename}))
        raise NoInitModule()

    # Figure out the full package name for the module and import it.
    init_mod_name = '%s.%s' % (os.path.basename(pack_name), init_mod_name)

    try:
        pack_module = __import__(init_mod_name)
    except ImportError:
        _LOG.exception(_('Could not load initialization module [%(m)s]' % {'m' : init_mod_name}))
        raise ImportFailed()

    # Get a handle on the initialize function
    try:
        cli_module = pack_module.pulp_cli
        init_func = getattr(cli_module, 'initialize')
    except AttributeError:
        _LOG.exception(_('Module [%(m)s] does not define the required initialize function' % {'m' : init_mod_name}))
        raise NoInitFunction()

    # Invoke the module's initialization, passing a copy of the context so
    # one extension doesn't accidentally muck with it and affect another.
    context_copy = copy.deepcopy(context)
    try:
        init_func(context_copy)
    except Exception:
        _LOG.exception(_('Module [%(m)s] could not be initialized' % {'m' : init_mod_name}))
        raise InitError()
