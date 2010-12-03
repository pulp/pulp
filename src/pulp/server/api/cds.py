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
from pulp.server.api.cds_history import CdsHistoryApi
from pulp.server.api.repo import RepoApi
from pulp.server.auditing import audit
from pulp.server.db.connection import get_object_db
from pulp.server.db.model import CDS
from pulp.server.pexceptions import PulpException


log = logging.getLogger(__name__)


class CdsApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.repo_api = RepoApi()
        self.cds_history_api = CdsHistoryApi()

    def _getcollection(self):
        return get_object_db('cds', ['hostname'], self._indexes)

# -- public api ---------------------------------------------------------------------

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

        self.cds_history_api.cds_registered(hostname)

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

        self.cds_history_api.cds_unregistered(hostname)

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

        @return: list of all registered CDS instances; empty list if none are registered
        @rtype:  list
        '''
        return list(self.objectdb.find())

    def associate_repo(self, cds_hostname, repo_id):
        '''
        Associates a repo with a CDS. All data in an associated repo will be kept synchronized
        when the CDS synchronization occurs. This call will not cause the initial
        synchronization of the repo to occur to this CDS; that must be explicitly done through
        a separate call or picked up during the next scheduled sync for the CDS. This call has
        no effect if the given repo is already associated with the given CDS.

        @param cds_hostname: identifies the CDS to associate the repo with; the CDS entry
                             must exist prior to this call
        @type  cds_hostname: string; may not be None

        @param repo_id: identifies the repo to associate with the CDS; the repo must exist
                        prior to this call
        @type  repo_id: string; may not be None

        @raise PulpException: if the CDS or repo does not exist
        '''

        # Entity load and sanity check on the arguments
        cds = self.cds(cds_hostname)
        if cds is None:
            raise PulpException('CDS with hostname [%s] could not be found' % cds_hostname)

        repo = self.repo_api.repository(repo_id)
        if repo is None:
            raise PulpException('Repository with ID [%s] could not be found' % repo_id)

        if repo_id not in cds['repo_ids']:
            cds['repo_ids'].append(repo_id)

        self.objectdb.save(cds, safe=True)

        self.cds_history_api.repo_associated(cds_hostname, repo_id)

    def unassociate_repo(self, cds_hostname, repo_id):
        '''
        Removes an existing association between a CDS and a repo. This call will not cause
        the repo data to be deleted from the CDS; that must be explicitly done through
        a separate call or picked up during the next scheduled sync for the CDS. This call has
        no effect if the given repo is not associated with the given CDS.

        @param cds_hostname: identifies the CDS to remove the repo association; the CDS entry
                             must exist prior to this call
        @type  cds_hostname: string; may not be None

        @param repo_id: identifies the repo to unassociate from the CDS
        @type  repo_id: string; may not be None

        @raise PulpException: if the CDS does not exist
        '''

        # Entity load and sanity check on the arguments
        cds = self.cds(cds_hostname)
        if cds is None:
            raise PulpException('CDS with hostname [%s] could not be found' % cds_hostname)

        if repo_id in cds['repo_ids']:
            cds['repo_ids'].remove(repo_id)

        self.objectdb.save(cds, safe=True)

        self.cds_history_api.repo_unassociated(cds_hostname, repo_id)

    def sync(self, cds_hostname):
        '''
        Causes a CDS to be triggered to synchronize all of its repos as soon as possible,
        regardless of when its next scheduled sync would be. The CDS will be brought up to
        speed with all repos it is currently associated with, including deleting repos that
        are no longer associated with the CDS.

        @param cds_hostname: identifies the CDS
        @type  cds_hostname: string; may not be None

        @raise PulpException: if the CDS does not exist
        '''

        # Entity load and sanity check on the arguments
        cds = self.cds(cds_hostname)
        if cds is None:
            raise PulpException('CDS with hostname [%s] could not be found' % cds_hostname)

        # Call out to dispatcher to trigger sync
        # Dispatcher will do the history additions since the call will be async
               
# -- internal only api ---------------------------------------------------------------------

    def unassociate_all_from_repo(self, repo_id):
        '''
        Unassociates all CDS instances that are associated with the given repo. This is
        meant to be called in response to a repo being deleted. Unlike the unassociate call
        that requires an explicit sync, this call will trigger a message to be sent to each
        CDS to remove the repo. The rationale is that if a repo is deleted, we want it to
        be deleted everywhere as soon as possible without having to make the user explicitly
        trigger syncs on all CDS instances that may have the repo.
        '''

        # Find all CDS instances associated with the given repo
        cds_list = self.objectdb.find({'repo_ids': {'$exists': True}})

        # Queue calls to the CDS to unassociate

        for cds in cds_list:
            cds['repo_ids'].remove(repo_id)
            self.objectdb.save(cds, safe=True)

            self.cds_history_api.repo_unassociated(cds['hostname'], repo_id)
