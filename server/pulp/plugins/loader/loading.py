import logging
import os
import re
import sys
from gettext import gettext as _

import pkg_resources

from pulp.common.compat import json


_logger = logging.getLogger(__name__)

# file types
_CONFIG_REGEX = re.compile('.*\.(config|conf|cfg)$', re.IGNORECASE)
_INIT_REGEX = re.compile('__init__.py(c|o)?$')


class ConfigParsingException(Exception):
    """
    :ivar config_file: full path to the plugin conf file that failed to load
    :type config_file: str
    """

    def __init__(self, config_file):
        super(ConfigParsingException, self).__init__()
        self.config_file = config_file

    def __str__(self):
        return 'Invalid configuration file: %s' % self.config_file


def add_plugin_to_map(cls, cfg, plugin_map):
    """
    Add a plugin and its config to the given plugin map

    @param cls: class for the plugin
    @param cfg: config for the plugin
    @type  cfg: dict
    @param plugin_map: pulp.plugins.loader.manager._PluginMap instance
    """
    id = get_plugin_metadata_field(cls, 'id', cls.__name__)
    types = get_plugin_types(cls)
    if None in (id, types):
        return
    plugin_map.add_plugin(id, cls, cfg, types)


def load_plugins_from_entry_point(entry_point_group_name, plugin_map):
    """
    Load plugins by looking for entry points. Packages providing plugins should
    advertise them through entry point groups with names we pre-determine.

    @param entry_point_group_name: name of an entry point group
    @param plugin_map: plugin map to which plugins should be added
    @type  plugin_map: pulp.plugins.loader.manager._PluginMap instance
    """
    for entry_point in pkg_resources.iter_entry_points(entry_point_group_name):
        _logger.debug('Loading %s' % entry_point)
        cls, cfg = entry_point.load()()
        add_plugin_to_map(cls, cfg, plugin_map)


def load_plugins(path, base_class, module_name):
    """
    @type path: str
    @type base_class: type
    @type module_name: str
    @rtype: list of tuple (type, dict)
    """
    _logger.debug('Loading plugin: %s, %s, %s' % (path, base_class.__name__, module_name))

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
        _logger.error(msg % {'n': package_name})
        return None

    if not module_found:
        msg = _('Cannot load plugin: %(n)s has no module: %(p)s.%(m)s')
        _logger.info(msg % {'n': module_name.title(), 'p': package_name, 'm': module_name})
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
    _logger.debug('Loading plugin class: %s, %s' % (module_name, base_class.__name__))

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
        _logger.error(msg % {'m': module_name, 'c': base_class.__name__})

    return attr_list


def load_plugin_config(config_file_name):
    """
    @type config_file_name: str
    @rtype: dict
    """
    _logger.info('Loading config file: %s' % config_file_name)

    try:
        contents = read_content(config_file_name)
        cfg = json.loads(contents)
        return cfg
    except ValueError:
        # ValueError is raised if the config file isn't valid JSON
        _logger.error('Error parsing config file: %s' % config_file_name)
        raise ConfigParsingException(config_file_name)


def import_module(name):
    """
    @type name: str
    @rtype: module
    """
    _logger.debug('Importing plugin module: %s' % name)
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
    _logger.debug('Getting types for plugin class: %s' % plugin_class.__name__)
    types = get_plugin_metadata_field(plugin_class, 'types')
    if types is None:
        msg =  _('Cannot load plugin: %(p)s does not define any types')
        _logger.error(msg % {'p': plugin_class.__name__})
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
        _logger.error(msg % {'p': plugin_class.__name__})
        return None
    value = metadata.get(field, default)
    return value

# general utility methods ------------------------------------------------------

def add_path_to_sys_path(path):
    """
    @type path: str
    """
    _logger.debug('Adding path to sys.path: %s' % path)
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

