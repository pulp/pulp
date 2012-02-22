# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


# base api class --------------------------------------------------------------
import re
from gettext import gettext as _
from pulp.server.exceptions import PulpDataException


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

#    def insert(self, object, check_keys=False):
#        """
#        Insert the object document to the database
#        """
#        self.collection.insert(object, check_keys=check_keys, safe=True)
#        return object

#    def update(self, object):
#        """
#        Write the object document to the database
#        """
#        self.collection.save(object, safe=True)
#        return object

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

    def check_for_whitespace(self, id, entity_name='ID'):
        """
        Raise an exception if id contains whitespace characters
        """
        if re.search('\s', id):
            raise PulpDataException(_("Given %s:[%s] is invalid. %s should not contain whitespace characters." % (entity_name, id, entity_name)))

    def check_id(self, id):
        """
        Make sure id is compliant with restrictions defined by following regex
        """
        if re.search("[^\w\-.]", id):
            raise PulpDataException(_("Given ID is invalid. ID may contain numbers(0-9), upper and lower case letters(A-Z, a-z), hyphens(-), underscore(_) and periods(.)"))
    
