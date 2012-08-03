# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import logging
import os
import re
import sys
from gettext import gettext as _

try:
    import json
except ImportError:
    import simplejson as json

# constants --------------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# file types

_CONFIG_REGEX = re.compile('.*\.(config|conf|cfg)$', re.IGNORECASE)
_INIT_REGEX = re.compile('__init__.py(c|o)?$')

# plugin loading methods -------------------------------------------------------

def load_plugins_from_path(path, base_class, plugin_map):
    """
    @type path: str
    @type base_class: type
    @type plugin_map: L{_PluginMap}
    """
    _LOG.debug('Loading multiple plugins: %s, %s' % (path, base_class.__name__))

    if not os.access(path, os.F_OK | os.R_OK):
        msg = _('Cannot load plugins: path does not exist or cannot be read: %(p)s')
        _LOG.critical(msg % {'p': path})
        return

    add_path_to_sys_path(path)

    plugin_dirs = get_plugin_dirs(path)

    for dir_ in plugin_dirs:
        if dir_ in sys.modules:
            msg = _('Cannot load plugin: python already has module loaded: %(d)s')
            _LOG.error(msg % {'d': dir_})
            continue

        plugin_tuples = load_plugins(dir_, base_class, base_class.__name__.lower())

        if plugin_tuples is None:
            continue

        for cls, cfg in plugin_tuples:
            id = get_plugin_metadata_field(cls, 'id', cls.__name__)
            types = get_plugin_types(cls)
            if None in (id, types):
                continue
            plugin_map.add_plugin(id, cls, cfg, types)


def get_plugin_dirs(plugin_root):
    """
    @type plugin_root: str
    @rtype: list [str, ...]
    """
    _LOG.debug('Looking for plugin dirs in plugin root: %s' % plugin_root)
    dirs = []
    for entry in os.listdir(plugin_root):
        plugin_dir = os.path.join(plugin_root, entry)
        if not os.path.isdir(plugin_dir):
            continue
        dirs.append(plugin_dir)
    return dirs


def load_plugins(path, base_class, module_name):
    """
    @type path: str
    @type base_class: type
    @type module_name: str
    @rtype: list of tuple (type, dict)
    """
    _LOG.debug('Loading plugin: %s, %s, %s' % (path, base_class.__name__, module_name))

    config_path = None
    init_found = False
    module_found = False
    module_regex = re.compile('%s\.py(c|o)?$' % module_name)
    package_name = os.path.split(path)[-1]

    # grok through the directory looking for the plugin module and config
    for entry in os.listdir(path):
        if _INIT_REGEX.match(entry):
            init_found = True
        elif module_regex.match(entry):
            module_found = True
        elif _CONFIG_REGEX.match(entry):
            config_path = os.path.join(path, entry)

    if not init_found:
        msg = _('Cannot load plugin: %(n)s is not a package: no __init__.py found')
        _LOG.error(msg % {'n': package_name})
        return None

    if not module_found:
        msg = _('Cannot load plugin: %(n)s has no module: %(p)s.%(m)s')
        _LOG.info(msg % {'n': module_name.title(), 'p': package_name, 'm': module_name})
        return None

    # load and return the plugin class and configuration
    cls_list = load_plugin_classes('.'.join((package_name, module_name)), base_class)
    cfg = {}
    if config_path is not None:
        cfg = load_plugin_config(config_path)

    plugin_tuples = [(cls, cfg) for cls in cls_list]
    return plugin_tuples


def load_plugin_classes(module_name, base_class):
    """
    @type module_name: str
    @type base_class: type
    @rtype: list of attr
    """
    _LOG.debug('Loading plugin class: %s, %s' % (module_name, base_class.__name__))

    module = import_module(module_name)
    attr_list = []

    for attr_name in dir(module):
        # '_' prefixed modules contain non-loaded base plugin classes by convention
        if attr_name.startswith('_'):
            continue

        attr = getattr(module, attr_name)

        # to be loaded the attr must be a *derived* class of the base_class
        if not isinstance(attr, type):
            continue
        if not issubclass(attr, base_class):
            continue
        if attr is base_class:
            continue

        attr_list.append(attr)

    if len(attr_list) is 0:
        msg = _('Cannot load plugin: %(m)s modules did not contain a derived class of %(c)s')
        _LOG.error(msg % {'m': module_name, 'c': base_class.__name__})

    return attr_list


def load_plugin_config(config_file_name):
    """
    @type config_file_name: str
    @rtype: dict
    """
    _LOG.debug('Loading config file: %s' % config_file_name)
    contents = read_content(config_file_name)
    cfg = json.loads(contents)
    return cfg


def import_module(name):
    """
    @type name: str
    @rtype: module
    """
    _LOG.debug('Importing plugin module: %s' % name)
    if name in sys.modules:
        sys.modules.pop(name)
    mod = __import__(name)
    for sub in name.split('.')[1:]:
        mod = getattr(mod, sub)
    return mod


def get_plugin_types(plugin_class):
    """
    @type plugin_class: type
    @rtype: list [str, ...]
    """
    _LOG.debug('Getting types for plugin class: %s' % plugin_class.__name__)
    types = get_plugin_metadata_field(plugin_class, 'types')
    if types is None:
        msg =  _('Cannot load plugin: %(p)s does not define any types')
        _LOG.error(msg % {'p': plugin_class.__name__})
        return None
    if isinstance(types, basestring):
        types = [types]
    return types


def get_plugin_metadata_field(plugin_class, field, default=None):
    """
    @type plugin_class: type
    @type field: str
    @rtype: str
    """
    metadata = plugin_class.metadata()
    if not isinstance(metadata, dict):
        msg = _('Cannot load plugin: %(p)s.metadata() did not return a dictionary')
        _LOG.error(msg % {'p': plugin_class.__name__})
        return None
    value = metadata.get(field, default)
    return value

# general utility methods ------------------------------------------------------

def add_path_to_sys_path(path):
    """
    @type path: str
    """
    _LOG.debug('Adding path to sys.path: %s' % path)
    if path in sys.path:
        return
    sys.path.append(path)


def read_content(file_name):
    """
    @type file_name: str
    @rtype: str
    """
    handle = open(file_name, 'r')
    contents = handle.read()
    handle.close()
    return contents

