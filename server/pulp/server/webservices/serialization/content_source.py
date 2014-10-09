import link

from pulp.server.content.sources import constants


def serialize(source):
    """
    Get a REST object representation of a content source model object.
    :param source: A content source model object.
    :type source: pulp.server.content.sources.model.ContentSource
    :return: A dict representations of the model object.
    :rtype: dict
    """
    serial = {}
    serial.update(source.descriptor)
    serial[constants.SOURCE_ID] = source.id
    serial[constants.PRIORITY] = source.priority
    serial[constants.EXPIRES] = source.expires
    serial[constants.URL] = source.urls
    serial[constants.MAX_CONCURRENT] = source.max_concurrent
    href = link.child_link_obj(source.id)
    serial.update(href)
    return serial
