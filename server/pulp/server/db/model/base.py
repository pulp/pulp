import logging

from pymongo import DESCENDING

from pulp.server.compat import ObjectId
from pulp.server.db.connection import get_collection


_logger = logging.getLogger(__name__)


class DoesNotExist(Exception):
    """
    This Exception can be raised by Managers or Models if they are asked to perform operations on
    records that do not exist.
    """
    pass


class Model(dict):
    """
    Model base class

    Derived model classes are the representation of persistent data used by
    pulp and are abstractions of the documents used by mongodb. These classes
    are used to create new documents to be stored in a document collection.

    The model base class is derived from the builtin dictionary, and should be
    used as such by code after instantiation. It provides a mechanism to use
    dot notation instead of the usual dictionary key lookup. However, this is
    provided for convenience when declaring fields in the constructors, and
    should not be used by code. Documents that are retrieved from a document
    collection are also derivatives of dictionaries, but are not derivatives
    of the Model class. To ensure interchangeability, make sure to use python's
    regular dictionary key lookup when using Model instances.
    """

    # The model class will know how to fetch the document collection used to
    # store the models in database. If you want a document collection to be
    # associated with your model, all you need to do is define the name of the
    # document collection with the 'collection_name' class field.
    # Once you have defined the collection_name, you may use the
    # 'unique_indices' and 'search_indices' to define which fields are indexed
    # in the document collection.
    # The unique_indices field is a tuple whose elements can be either:
    # * A string name of a model field whose value is to be indexed and must be
    #   unique among all stored instances of the model.
    # * A tuple of string names of model fields that will each be indexed and,
    #   together, must be a unique set of fields among all stored instances of
    #   the model.
    # The search_indices field is only a tuple listing other model fields to be
    # indexed in the collection, but that do not need to be individually unique
    # or form unique sets of values.

    collection_name = None
    unique_indices = ('id',)  # note, '_id' is automatically unique and indexed
    search_indices = ()
    _collection = None

    def __init__(self):
        self._id = ObjectId()
        self.id = str(self._id)  # legacy behavior, would love to rid ourselves of this

    # XXX only for use in constructors
    # dict to dot-notation mapping methods

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getstate__(self):
        return dict(self.items())

    def __setstate__(self, state):
        self.update(state)

    # database collection methods ---------------------------------------------

    @classmethod
    def _get_collection_from_db(cls):
        # ensure the indices in the document collection
        def _ensure_indices(collection, indices, unique):
            # indices are either tuples or strings,
            # tuples are 'unique together' if unique is True
            for index in indices:
                if isinstance(index, basestring):
                    index = (index,)
                # we're using descending ordering for the arbitrary case,
                # if you need a particular ordering, override the
                # _get_collection_from_db method
                collection.ensure_index([(i, DESCENDING) for i in index],
                                        unique=unique, background=True)
        # create the collection and ensure the unique and other indices
        collection = get_collection(cls.collection_name)
        _ensure_indices(collection, cls.unique_indices, True)
        _ensure_indices(collection, cls.search_indices, False)
        return collection

    @classmethod
    def get_collection(cls):
        """
        Get the document collection for this data model.
        :return: the document collection if associated with one, None otherwise
        :rtype: pymongo.collection.Collection instance or None
        """
        # not all data models are associated with a document collection
        # provide mechanism for sub-documents by not defining the
        # collection_name
        if cls.collection_name is None:
            return None
        if not cls._collection:
            cls._collection = cls._get_collection_from_db()
        return cls._collection
