from gettext import gettext as _

from pulp.plugins.profiler import Profiler
from pulp.server.config import config as pulp_conf
from pulp.server.managers import factory as managers

from pulp_node import constants
from pulp_node.config import read_config


def entry_point():
    """
    Entry point that pulp platform uses to load the profiler.
    :return: profiler class and its configuration.
    :rtype:  Profiler, dict
    """
    return NodeProfiler, {}


class NodeProfiler(Profiler):

    @classmethod
    def metadata(cls):
        """
        Plugin metadata.
        :return: The plugin metadata.
        :rtype: dict
        """
        return {
            'id': constants.PROFILER_ID,
            'display_name': _('Nodes Profiler'),
            'types': [constants.NODE_SCOPE, constants.REPOSITORY_SCOPE]
        }

    @staticmethod
    def _inject_parent_settings(options):
        """
        Inject the parent settings into the options.
        Add the pulp server host and port information to the options.
        Used by the agent handler to make REST calls back to the parent.
        :param options: An options dictionary.
        :type options: dict
        """
        port = 443
        host = pulp_conf.get('server', 'server_name')
        node_conf = read_config()
        path = node_conf.main.node_certificate
        with open(path) as fp:
            node_certificate = fp.read()
        settings = {
            constants.HOST: host,
            constants.PORT: port,
            constants.NODE_CERTIFICATE: node_certificate,
        }
        options[constants.PARENT_SETTINGS] = settings

    @staticmethod
    def _inject_strategy(consumer_id, options):
        """
        Inject the node-level synchronization strategy.
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param options: The update options.
        :type options: dict
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        strategy = consumer['notes'].get(constants.STRATEGY_NOTE_KEY)
        options[constants.STRATEGY_KEYWORD] = strategy

    def update_units(self, consumer, units, options, config, conduit):
        """
        Translate the specified content units to be updated.
        The specified content units are intended to be updated on the
        specified consumer.  It is requested that the profiler translate
        the units as needed.  If any of the content units cannot be translated,
        an exception should be raised by the profiler.  The translation itself,
        depends on the content unit type and is completely up to the Profiler.
        Translation into an empty list is not considered an error condition and
        will be interpreted by the caller as meaning that no content needs to be
        updated.

        @see: Unit Translation examples in class documentation.

        :param consumer: A consumer.
        :type consumer: pulp.plugins.model.Consumer

        :param units: A list of content units to be updated.
        :type units: list of: { type_id:<str>, unit_key:<dict> }

        :param options: Update options; based on unit type.
        :type options: dict

        :param config: plugin configuration
        :type config: pulp.plugins.config.PluginCallConfiguration

        :param conduit: provides access to relevant Pulp functionality
        :type conduit: pulp.plugins.conduits.profiler.ProfilerConduit

        :return: The translated units
        :rtype: list of: { type_id:<str>, unit_key:<dict> }

        :raises: InvalidUnitsRequested - if one or more of the units cannot be updated
        """
        self._inject_parent_settings(options)
        self._inject_strategy(consumer.id, options)
        return units
