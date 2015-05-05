"""
Module for scrubbing various db-only related fields from serialized documents.

NOTE: this is a utility module for use by other modules in this package and is
      not automatically imported when the package is imported.
"""


def scrub_mongo_fields(document):
    """
    Remove mongo db specific fields from the document.
    @param document: mongo db data document
    @type document: SON
    @return: document with mongo db fields removed
    @rtype: SON
    """
    # XXX not sure if this is correct behavior or not
    def _scrub_id(document):
        _id = document.get('_id', None)
        id = document.get('id', None)
        if _id == id:
            document.pop('_id', None)
        elif id is None:
            document['id'] = document.pop('_id', None)
        else:
            document.pop('_id', None)

    # _scrub_id(document)
    document.pop('_ns', None)
    return document
