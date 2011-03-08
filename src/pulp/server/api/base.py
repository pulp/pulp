# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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

# base api class --------------------------------------------------------------

class BaseApi(object):

    # database methods --------------------------------------------------------

    def _getcollection(self):
        """
        Protected method to get the db collection corresponding to this api.
        """
        raise NotImplementedError()

    @property
    def collection(self):
        return self._getcollection()

    # crud methods ------------------------------------------------------------

    def insert(self, object, check_keys=False):
        """
        Insert the object document to the database
        """
        self.collection.insert(object, check_keys=check_keys, safe=True)
        return object

    def update(self, object):
        """
        Write the object document to the database
        """
        self.collection.save(object, safe=True)
        return object

    def delete(self, **kwargs):
        """
        Delete a single stored Object
        """
        self.collection.remove(kwargs, safe=True)

    def clean(self):
        """
        Delete all the Objects in the database.  WARNING: Destructive
        """
        self.collection.remove(safe=True)
