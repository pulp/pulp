# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


from pymongo.errors import DuplicateKeyError
from pulp.server.db.model.audit import *
from pulp.server.db.model.auth import *
from pulp.server.db.model.cds import *
from pulp.server.db.model.status import *
from pulp.server.db.model.resource import *
from pulp.server.db.model.persistence import *


class Delta(dict):
    """
    The delta of a model object.
    Contains the primary key and keys/values specified in the filter.
    """

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, obj, filter=()):
        """
        @param obj: A model object (dict).
        @type obj: Model|dict
        @param filter: A list of dictionary keys to include
            in the delta.
        @type filter: str|list
        """
        dict.__init__(self)
        if isinstance(filter, basestring):
            filter = (filter,)
        for k,v in obj.items():
            if k in filter:
                self[k] = v
