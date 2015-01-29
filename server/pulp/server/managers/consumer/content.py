"""
Contains content management classes.
"""

from pulp.server.db.model.consumer import Consumer
from pulp.server.exceptions import MissingResource
from pulp.server.agent.direct.pulpagent import PulpAgent


class ConsumerContentManager(object):
    """
    Provies content management on a consumer
    """

    def install(self, id, units, options={}):
        """
        Install content on a consumer.
        @param id: A consumer id.
        @type id: str
        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Install options; based on unit type.
        @type options: dict
        """
        collection = Consumer.get_collection()
        consumer = collection.find_one({'id': id})
        if consumer is None:
            raise MissingResource(id)
        agent = PulpAgent(consumer)
        agent.install_units(units, options)

    def update(self, id, units, options={}):
        """
        Update content on a consumer.
        @param id: A consumer id.
        @type id: str
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        """
        collection = Consumer.get_collection()
        consumer = collection.find_one({'id': id})
        if consumer is None:
            raise MissingResource(id)
        agent = PulpAgent(consumer)
        agent.update_units(units, options)

    def uninstall(self, id, units, options={}):
        """
        Uninstall content on a consumer.
        @param id: A consumer id.
        @type id: str
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        """
        collection = Consumer.get_collection()
        consumer = collection.find_one({'id': id})
        if consumer is None:
            raise MissingResource(id)
        agent = PulpAgent(consumer)
        agent.uninstall_units(units, options)
