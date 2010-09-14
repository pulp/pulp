#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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

from pulp.server import async

# base api class --------------------------------------------------------------

class BaseApi(object):

    def __init__(self):
        self.objectdb = self._getcollection()

    # db indexes

    @property
    def _unique_indexes(self):
        return ["id"]

    @property
    def _indexes(self):
        return []

    # db methods

    def clean(self):
        """
        Delete all the Objects in the database.  WARNING: Destructive
        """
        self.objectdb.remove(safe=True)

    def insert(self, object, check_keys=False):
        """
        Insert the object document to the database
        """
        self.objectdb.insert(object, check_keys=check_keys, safe=True)
        return object

    def update(self, object):
        """
        Write the object document to the database
        """
        self.objectdb.save(object, safe=True)
        return object

    def delete(self, **kwargs):
        """
        Delete a single stored Object
        """
        self.objectdb.remove(kwargs, safe=True)

    def _getcollection(self):
        """
        Protected method to get the db collection corresponding to this api.
        """
        raise NotImplementedError()

    # async methods

    def run_async(self, method, args, kwargs, timeout=None):
        return async.run_async(method, args, kwargs, timeout)

    def find_async(self, **kwargs):
        return async.find_async(**kwargs)

    def cancel_async(self, task):
        return async.cancel_async(task)
