from pulp.server.db.model.event import EventListener


def migrate(*args, **kwargs):
    """
    Change the type id from 'rest-api' to 'http'
    """
    collection = EventListener.get_collection()
    collection.update({'notifier_type_id': 'rest-api'}, {'$set': {'notifier_type_id': 'http'}})
