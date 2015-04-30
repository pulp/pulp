from gettext import gettext as _
from pprint import pformat
import copy
import logging
import pkg_resources

from mongoengine import signals

from pulp.common import error_codes
from pulp.plugins.loader import exceptions as loader_exceptions
from pulp.server.db.model import ContentUnit
from pulp.server.exceptions import PulpCodedException


_logger = logging.getLogger(__name__)

ENTRY_POINT_UNIT_MODELS = 'pulp.unit_models'


class PluginManager(object):
    """
    Class to manage heterogeneous types of plugins including their class,
    configuration, and supported types associations.
    """

    def __init__(self):
        self.distributors = _PluginMap()
        self.group_distributors = _PluginMap()
        self.group_importers = _PluginMap()
        self.importers = _PluginMap()
        self.profilers = _PluginMap()
        self.catalogers = _PluginMap()
        self.unit_models = dict()

        # Load the unit models
        self._load_unit_models()

    def _load_unit_models(self):
        """"
        Load all of the Unit Models from the ENTRY_POINT_UNIT_MODELS entry point

        Attach the signals to the models here since the mongoengine signals will not be
        sent correctly if they are attached to the base class.

        :raises: PLP0038 if two models are defined with the same id
        :raises: PLP0039 if a model is not a subclass of ContentUnit
        """
        _logger.debug(_("Loading Unit Models"))
        for entry_point in pkg_resources.iter_entry_points(ENTRY_POINT_UNIT_MODELS):
            msg = _('Loading unit model: %s' % str(entry_point))
            _logger.info(msg)
            model_id = entry_point.name
            model_class = entry_point.load()
            class_name = model_class.__class__.__module__ + "." + model_class.__class__.__name__
            if not issubclass(model_class, ContentUnit):
                raise PulpCodedException(error_code=error_codes.PLP0039,
                                         model_id=model_id,
                                         model_class=class_name)

            if model_id in self.unit_models:
                raise PulpCodedException(error_code=error_codes.PLP0038,
                                         model_id=model_id,
                                         model_class=class_name)
            self.unit_models[model_id] = model_class

            # Attach all the signals
            model_class.attach_signals()
            signals.post_init.connect(model_class.post_init_signal, sender=model_class)
            signals.pre_save.connect(model_class.pre_save_signal, sender=model_class)

        _logger.debug(_("Unit Model Loading Completed"))


class _PluginMap(object):
    """
    Convenience class for managing plugins of a homogeneous type.
    @ivar configs: dict of associated configurations
    @ivar plugins: dict of associated classes
    @ivar types: dict of supported types the plugins operate on
    """

    def __init__(self):
        self.configs = {}
        self.plugins = {}
        self.types = {}

    def add_plugin(self, id, cls, cfg, types=()):
        """
        @type id: str
        @type cls: type
        @type cfg: dict
        @type types: list or tuple
        """
        if not cfg.get('enabled', True):
            _logger.info(_('Skipping plugin %(p)s: not enabled') % {'p': id})
            return
        if self.has_plugin(id):
            msg = _('Plugin with same id already exists: %(n)s')
            raise loader_exceptions.ConflictingPluginName(msg % {'n': id})
        self.plugins[id] = cls
        self.configs[id] = cfg
        for type_ in types:
            plugin_ids = self.types.setdefault(type_, [])
            plugin_ids.append(id)
        _logger.info(_('Loaded plugin %(p)s for types: %(t)s') %
                     {'p': id, 't': ','.join(types)})
        _logger.debug('class: %s; config: %s' % (cls.__name__, pformat(cfg)))

    def get_plugin_by_id(self, id):
        """
        @type id: str
        @rtype: tuple (type, dict)
        @raises L{PluginNotFound}
        """
        if not self.has_plugin(id):
            raise loader_exceptions.PluginNotFound(_('No plugin found: %(n)s') % {'n': id})
        # return a deepcopy of the config to avoid persisting external changes
        return self.plugins[id], copy.deepcopy(self.configs[id])

    def get_plugins_by_type(self, type_):
        """
        @type type_: str
        @rtype: list of tuples (cls, config)
        @raise: L{exceptions.PluginNotFound}
        """
        ids = self.get_plugin_ids_by_type(type_)
        return [(self.plugins[id], self.configs[id]) for id in ids]

    def get_plugin_ids_by_type(self, type_):
        """
        @type type_: str
        @rtype: tuple (str, ...)
        @raises L{PluginNotFound}
        """
        plugins = self.types.get(type_, [])
        if not plugins:
            raise loader_exceptions.PluginNotFound(_('No plugin found for: %(t)s') % {'t': type_})
        return tuple(plugins)

    def get_loaded_plugins(self):
        """
        @rtype: dict {str: dict, ...}
        """
        return dict((id, cls.metadata()) for id, cls in self.plugins.items())

    def has_plugin(self, id):
        """
        @type id: str
        @rtype: bool
        """
        return id in self.plugins

    def remove_plugin(self, id):
        """
        @type id: str
        """
        if not self.has_plugin(id):
            return
        self.plugins.pop(id)
        self.configs.pop(id)
        for type_, ids in self.types.items():
            if id not in ids:
                continue
            ids.remove(id)
