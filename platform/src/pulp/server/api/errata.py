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

import logging

from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.exceptions import PulpException

log = logging.getLogger(__name__)

errata_fields = model.Errata(None, None, None, None, None, None).keys()

class ErrataHasReferences(Exception):

    MSG = 'errata [%s] has references, delete not permitted'

    def __init__(self, id):
        Exception.__init__(self, self.MSG % id)

class ErrataApi(BaseApi):

    def _getcollection(self):
        return model.Errata.get_collection()

    @audit(params=["id", "title", "type"])
    def create(self, id, title, description, version, release, type,
            status="", updated="", issued="", pushcount="", from_str="",
            reboot_suggested="", references=(), pkglist=(), severity="",
            rights="", summary="", solution="", repo_defined=False, 
            immutable=False, repoids=[]):
        """
        Create a new Errata object and return it
        """
        e = model.Errata(id, title, description, version, release, type,
                status, updated, issued, pushcount, from_str,
                reboot_suggested, references, pkglist, severity, rights,
                summary, solution, repo_defined, immutable, repoids)
        self.collection.insert(e, safe=True)
        return e

    @audit()
    def update(self, id, delta):
        """
        Updates an errata object.
        @param id: The repo ID.
        @type id: str
        @param delta: A dict containing update keywords.
        @type delta: dict
        @return: The updated object
        @rtype: dict
        """
        delta.pop('id', None)
        erratum = self.erratum(id)
        if not erratum:
            raise Exception('Erratum "%s", not-found', id)
        valid_keys = ['status', 'updated', 'short', 'severity', 'title', 'issued', 'id', 'rights', 'solution',
                      'summary', 'pushcount', 'fromstr', 'version', 'release', 'type', 'pkglist', 'description']
        for key, value in delta.items():
            if key in valid_keys:
                erratum[key] = value
                continue
            # unsupported
            raise Exception, \
                  'update keyword "%s", not-supported' % key
        self.collection.save(erratum, safe=True)
        return erratum

    @audit()
    def delete(self, id):
        """
        Delete errata object by id key
        """
        if self.referenced(id):
            raise ErrataHasReferences(id)
        self.collection.remove(dict(id=id))

    def referenced(self, id):
        """
        check if errata has references.
        @param id: A errata ID.
        @type id: str
        @return: True if referenced
        @rtype: bool
        """
        erratum = self.erratum(id, fields=['id', 'type'])
        if erratum is None:
            return False

        type = erratum["type"]
        collection = model.Repo.get_collection()
        query = "errata.%s" % type
        repo = collection.find_one({query:id}, fields=["id"])
        return (repo is not None)

    def erratum(self, id, fields=None):
        """
        Return a single Errata object based on the id
        """
        return self.collection.find_one({'id': id}, fields=fields)

    def search_errata(self, spec=None):
        """
        Return errata according to given spec
        """
        return list(self.collection.find(spec, ['id', 'title', 'type']))

    def errata(self, id=None, title=None, description=None, version=None,
            release=None, type=None, status=None, updated=None, issued=None,
            pushcount=None, from_str=None, reboot_suggested=None, severity=None,
            repo_defined=None, bzid=None, cve=None):
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
        if severity:
            searchDict['severity'] = severity
        if repo_defined is not None:
            searchDict['repo_defined'] = False
        if bzid:
            searchDict['references.id'] = bzid
            searchDict['references.type'] = "bugzilla"
        if cve:
            searchDict['references.id'] = cve
            searchDict['references.type'] = "cve"
        
        if (len(searchDict.keys()) == 0):
            return list(self.collection.find())
        else:
            return list(self.collection.find(searchDict))

    def search_by_packages(self):
        """
        Search for errata that are associated with specified package info
        """
        pass

    def search_by_issued_date_range(self):
        pass

