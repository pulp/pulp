from pulp.server.db.model.consumer import Bind


def migrate(*args, **kwargs):
    """
    Adds attributes needed for binding configurations. To maintain backward compatibility,
    the notify_agent field is set to True.
    """

    additions = (
        ('notify_agent', True),
        ('binding_config', None),
    )
    collection = Bind.get_collection()
    for bind in collection.find({}):
        dirty = False
        for key, value in additions:
            if key not in bind:
                bind[key] = value
                dirty = True
        if dirty:
            collection.save(bind)
