import link

from pulp.server.content.sources import constants


def serialize_all(sources):
    """
    Get a REST object representation of a collection of content source model objects.
    :param sources: A collection of content source model objects.
    :type sources: iterable
    :return: The REST objects.
    :rtype: generator
    """
    for source in sources:
        serialized = serialize(source)
        href = link.child_link_obj(serialized[constants.SOURCE_ID])
        serialized.update(href)
        yield serialized


def serialize(source):
    """
    Get a REST object representation of a content source model object.
    :param source: A content source model object.
    :type source: pulp.server.content.sources.model.ContentSource
    :return: The REST object.
    :rtype: dict
    """
    serialized = {}
    serialized.update(source.descriptor)
    serialized[constants.SOURCE_ID] = source.id
    serialized[constants.PRIORITY] = source.priority
    serialized[constants.EXPIRES] = source.expires
    serialized[constants.URL] = source.urls
    serialized[constants.MAX_CONCURRENT] = source.max_concurrent
    return serialized
