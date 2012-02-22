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

from ConfigParser import SafeConfigParser
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

_CONF_FILENAME = 'extension.conf'

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

class LoadFailed(ExtensionLoaderException):
    """
    Raised if one or more of the extensions failed to load. All failed
    extensions will be listed in the exception, however the causes are logged
    rather than carried in this exception.
    """
    def __init__(self, failed_packs):
        super(ExtensionLoaderException, self).__init__()
        self.failed_packs = failed_packs

    def __str__(self):
        return _('The following extension packs failed to load: [%s]' % ', '.join(self.failed_packs))

# Unit test marker exceptions
class ImportFailed(ExtensionLoaderException): pass
class NoInitFunction(ExtensionLoaderException): pass
class InitError(ExtensionLoaderException): pass
class InvalidExtensionConfig(ExtensionLoaderException): pass

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

    # Handle each extension pack in the directory in alphabetical order so
    # we can guarantee the loading order
    pack_names = sorted(os.listdir(extensions_dir))
    error_packs = []
    for pack in pack_names:
        try:
            _load_pack(extensions_dir, pack, context)
        except ExtensionLoaderException:
            # Do a best-effort attempt to load all extensions. If any fail,
            # the cause will be logged by _load_pack. This method should
            # continue to load extensions so all of the errors are logged.
            error_packs.append(pack)

    if len(error_packs) > 0:
        raise LoadFailed(error_packs)

def _load_pack(extensions_dir, pack_name, context):

    # Add the extensions directory to the path so each extension can be
    # loaded as a python module
    if extensions_dir not in sys.path:
        sys.path.append(extensions_dir)

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
        _LOG.info(_('No plugin initialization module [%(m)s] found, skipping initialization' % {'m' : init_mod_filename}))
        return

    # Figure out the full package name for the module and import it.
    init_mod_name = '%s.%s' % (os.path.basename(pack_name), init_mod_name)

    try:
        pack_module = __import__(init_mod_name)
    except Exception, e:
        _LOG.exception(_('Could not load initialization module [%(m)s]' % {'m' : init_mod_name}))
        raise ImportFailed(), None, sys.exc_info()[2]

    # Get a handle on the initialize function
    try:
        cli_module = pack_module.pulp_cli
        init_func = getattr(cli_module, 'initialize')
    except AttributeError, e:
        _LOG.exception(_('Module [%(m)s] does not define the required initialize function' % {'m' : init_mod_name}))
        raise NoInitFunction(), None, sys.exc_info()[2]

    # If the extension has a config file, load it
    conf_filename = os.path.join(extensions_dir, pack_name, _CONF_FILENAME)
    ext_config = None
    if os.path.exists(conf_filename):
        ext_config = SafeConfigParser()
        try:
            ext_config.read(conf_filename)
        except Exception, e:
            _LOG.exception(_('Could not read config file [%(f)s] for pack [%(p)s]' % {'f' : conf_filename, 'p' : pack_name}))
            raise InvalidExtensionConfig(), None, sys.exc_info()[2]

    # Invoke the module's initialization, passing a copy of the context so
    # one extension doesn't accidentally muck with it and affect another.
    context_copy = copy.copy(context)
    context_copy.client_config = copy.copy(context.client_config)
    context_copy.extension_config = ext_config

    try:
        init_func(context_copy)
    except Exception, e:
        _LOG.exception(_('Module [%(m)s] could not be initialized' % {'m' : init_mod_name}))
        raise InitError(), None, sys.exc_info()[2]
