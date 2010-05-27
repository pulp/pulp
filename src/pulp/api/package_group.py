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

# Pulp
from pulp import model
from pulp.api.base import BaseApi

class PackageGroupApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)

    def _getcollection(self):
        return self.db.packagegroups
    
    def update(self, object):
        """
        Override BaseApi 'update' so we may force the xml file on disk to be 
        updated with any changes that have been made. Afterwards we will 
        write the object document to the database
        """
        # comps.Comps()
        # Add in Groups & Categories
        # write out comps.Comps().xml()
        self.objectdb.save(object)

    def create(self, groupid, name, description, user_visible=False,
            display_order=1024, default=False, langonly=None):
        """
        Create a new PackageGroup object and return it
        """
        pg = model.PackageGroup(groupid, name, description, 
                user_visible=user_visible, display_order=display_order, 
                default=default, langonly=langonly)
        self.objectdb.insert(pg)
        return pg
        
    def packagegroup(self, id, filter=None):
        """
        Return a single PackageGroup object
        """
        return self.objectdb.find_one({'id': id})

    def packagegroups(self):
        """
        List all packagegroups.  Can be quite large
        """
        return list(self.objectdb.find())

