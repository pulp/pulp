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

# Python
import logging

# Pulp
from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db.connection import get_object_db
from pulp.server.db.model import CDS
from pulp.server.pexceptions import PulpException

log = logging.getLogger(__name__)


class CdsApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)

    def _getcollection(self):
        return get_object_db('cds', self._unique_indexes, self._indexes)

    @audit()
    def register(self, hostname, name=None, description=None):
        '''
        Registers the instance identified by hostname as a CDS in use by this pulp server.
        Before adding the CDS information to the pulp database, the CDS will be initialized.
        If the CDS cannot be initialized for whatever reason (CDS improperly configured,
        communications failure, etc) the CDS entry will not be added to the pulp database.
        If the entry was created, the representation will be returned from this call.

        @param hostname: fully-qualified hostname for the CDS instance
        @type  hostname: string; cannot be None

        @param name: user-friendly name that briefly describes the CDS; if None, the hostname
                     will be used to populate this field
        @type  name: string or None

        @param description: description of the CDS; may be None
        @type  description: string or None

        @raise PulpException: if the CDS already exists, the hostname is unspecified, or
                              the CDS initialization fails
        '''
        if not hostname:
            raise PulpException('Hostname cannot be empty')

        existing_cds = self.cds(hostname)

        if existing_cds:
            raise PulpException('CDS already exists with hostname [%s]' % hostname)

        # Add call here to fire off initialize call to the CDS

        cds = CDS(hostname, name, description)
        self.insert(cds)

        return cds

    @audit()
    def unregister(self, hostname):
        '''
        Unassociates an existing CDS from this pulp server.

        @param hostname: fully-qualified hostname of the CDS instance; a CDS instance must
                         exist with the given hostname
        @type  hostname: string; cannot be None

        @raise PulpException: if a CDS with the given hostname doesn't exist
        '''
        doomed = self.cds(hostname)

        if not doomed:
            raise PulpException('Could not find CDS with hostname [%s]' % hostname)

        # Add call here to fire off unregister call to the CDS
        # Decide what should happen if the unregister fails

        self.objectdb.remove({'hostname' : hostname}, safe=True)

    def cds(self, hostname):
        '''
        Returns the CDS instance that has the given hostname if one exists.

        @param hostname: fully qualified hostname of the CDS instance
        @type  hostname: string

        @return: CDS instance if one exists with the exact hostname given; None otherwise
        @rtype:  L{pulp.server.db.model.CDS} or None
        '''
        matching_cds = list(self.objectdb.find(spec={'hostname': hostname}))
        if len(matching_cds) == 0:
            return None
        else:
            return matching_cds[0]

    def list(self):
        '''
        Lists all CDS instances.     
        '''
        return list(self.objectdb.find())
