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

from pulp import model
from pulp.api.base import BaseApi
from pulp.auditing import audit


errata_fields = model.Errata(None, None, None, None, None, None).keys()


class ErrataApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)

    def _get_indexes(self):
        return ["title", "description", "version", "release", "type", "status",
                "updated", "issued", "pushcount", "from_str",
                "reboot_suggested"]

    def _getcollection(self):
        return self.db.errata

    @audit('ErrataApi')
    def create(self, id, title, description, version, release, type,
            status="", updated="", issued="", pushcount="", from_str="",
            reboot_suggested="", references=[], pkglist=[],
            repo_defined=False, immutable=False):
        """
        Create a new Errata object and return it
        """
        e = model.Errata(id, title, description, version, release, type,
                status, updated, issued, pushcount, from_str,
                reboot_suggested, references, pkglist, repo_defined,
                immutable)
        self.insert(e)
        return e

    @audit('ErrataApi')
    def delete(self, id):
        """
        Delete package version object based on "_id" key
        """
        super(ErrataApi, self).delete(id=id)

    @audit('ErrataApi', params=[])
    def update(self, object):
        """
        Updates an errata object in the database
        """
        return super(ErrataApi, self).update(object)

    def erratum(self, id):
        """
        Return a single Errata object based on the id
        """
        return self.objectdb.find_one({'id': id})

    def errata(self, id=None, title=None, description=None, version=None,
            release=None, type=None, status=None, updated=None, issued=None,
            pushcount=None, from_str=None, reboot_suggested=None):
        """
        Return a list of all errata objects matching search terms
        """
        searchDict = {}
        if id:
            searchDict['id'] = id
        if title:
            searchDict['title'] = title
        if description:
            searchDict['description'] = description
        if version:
            searchDict['version'] = version
        if release:
            searchDict['release'] = release
        if type:
            searchDict['type'] = type
        if status:
            searchDict['status'] = status
        if updated:
            searchDict['updated'] = updated
        if issued:
            searchDict['issued'] = issued
        if pushcount:
            searchDict['pushcount'] = pushcount
        if from_str:
            searchDict['from_str'] = from_str
        if reboot_suggested:
            searchDict['reboot_suggested'] = reboot_suggested
        if (len(searchDict.keys()) == 0):
            return list(self.objectdb.find())
        else:
            return list(self.objectdb.find(searchDict))

    def search_by_packages(self):
        """
        Search for errata that are associated with specified package info
        """
        pass

    def search_by_issued_date_range(self):
        pass

    def search_by_references(self):
        """
        Search Errata for specific info matching a reference
        Example: CVE id search
        """
        pass

    def search_by_repo(self, errata_id):
        """
        Goal is to return the repoid's of repos that contain this errata
        """
        pass
