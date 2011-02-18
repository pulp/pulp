# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import uuid
from gettext import gettext as _

from pymongo import DESCENDING
from pymongo.collection import Collection

from pulp.server.db.connection import get_database


class Model(dict):
    '''
    Model object that has convenience methods to get and put
    attrs into the base dict object with dot notation
    '''

    collection_name = None
    unique_indicies = ('id',) # note, '_id' is automatically unique and indexed
    other_indicies = ()

    def __init__(self):
        self._id = str(uuid.uuid4())
        self.id = self._id

    def __getattr__(self, attr):
        return self.get(attr, None)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    @classmethod
    def get_collection(cls):
        """
        Get the document collection for this data model.
        @rtype: pymongo.collection.Collection instance or None
        @return: the document collection if associated with one, None otherwise
        """

        # ensure the indicies in the document collection
        def _ensure_indicies(collection, indicies, unique):
            # indicies are either tuples or strings,
            # tuples are 'unique together' if unique is True
            for index in indicies:
                if isinstance(index, basestring):
                    index = (index,)
                collection.ensure_index([(i, DESCENDING) for i in index],
                                        unique=unique, background=True)

        # not all data models are associated with a document collection
        # provide mechanism for sub-documents
        if cls.collection_name is None:
            return None
        db = get_database()
        if db is None:
            msg = _('Cannot get collection from uninitialized database')
            raise RuntimeError(msg)
        collection = Collection(db, cls.collection_name)
        _ensure_indicies(collection, cls.unique_indicies, True)
        _ensure_indicies(collection, cls.other_indicies, False)
        return collection
