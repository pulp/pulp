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

# Python
import datetime
import logging
import sys

# Pulp
from pulp.repo_auth.repo_cert_utils import RepoCertUtils
import pulp.server.agent
import pulp.server.cds.round_robin as round_robin
import pulp.server.consumer_utils as consumer_utils
from pulp.server import config
from pulp.server.api.base import BaseApi
from pulp.server.api.cds_history import CdsHistoryApi
from pulp.server.api.scheduled_sync import update_cds_schedule, delete_cds_schedule
from pulp.server.auditing import audit
from pulp.server.cds.dispatcher import (
    GoferDispatcher, CdsTimeoutException, CdsCommunicationsException,
    CdsAuthException, CdsMethodException,)
from pulp.server.db.model import CDS, Repo
from pulp.server.pexceptions import PulpException


log = logging.getLogger(__name__)

REPO_FIELDS = [
    'id',
    'source',
    'name',
    'arch',
    'relative_path',
    'publish',
]


class CdsApi(BaseApi):

    def __init__(self):
        self.cds_history_api = CdsHistoryApi()
        self.dispatcher = GoferDispatcher()

    def _getcollection(self):
        return CDS.get_collection()

    def _repocollection(self):
        '''
        Returns the repo collection. This isn't the best approach; we need a more general
        refactoring of DB access methods away from the logic APIs, in which case this method
        will go away.
        '''
        return Repo.get_collection()

# -- public api ---------------------------------------------------------------------

    @audit()
    def register(self, hostname, name=None, description=None, sync_schedule=None):
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
        @type  name: str or None

        @param description: description of the CDS; may be None
        @type  description: str or None

        @param sync_schedule: contains information on when recurring syncs should execute
        @type  sync_schedule: str

        @raise PulpException: if the CDS already exists, the hostname is unspecified, or
                              the CDS initialization fails
        '''
        if not hostname:
            raise PulpException('Hostname cannot be empty')

        existing_cds = self.cds(hostname)

        if existing_cds:
            raise PulpException('CDS already exists with hostname [%s]' % hostname)

        cds = CDS(hostname, name, description)
        cds.sync_schedule = sync_schedule

        # Add call here to fire off initialize call to the CDS
        # and pdate the shared secret
        try:
            secret = self.dispatcher.init_cds(cds)
            cds.secret = secret
        except CdsTimeoutException:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise PulpException('Timeout occurred attempting to initialize CDS [%s]' % hostname), None, exc_traceback
        except CdsCommunicationsException:
            log.exception('Communications exception occurred initializing CDS [%s]' % hostname)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise PulpException('Communications error while attempting to initialize CDS [%s]; check the server log for more information' % hostname), None, exc_traceback
        except CdsAuthException:
            log.exception('Authorization exception occurred initializing CDS [%s]' % hostname)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise PulpException('Communications error while attempting to initialize CDS [%s]; check the server log for more information' % hostname), None, exc_traceback
        except CdsMethodException:
            log.exception('CDS error encountered while attempting to initialize CDS [%s]' % hostname)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise PulpException('CDS error encountered while attempting to initialize CDS [%s]; check the server log for more information' % hostname), None, exc_traceback

        self.collection.insert(cds, safe=True)

        self.cds_history_api.cds_registered(hostname)

        # Send the latest global repo auth credentials out to the CDS
        repo_cert_utils = RepoCertUtils(config.config)
        bundle = repo_cert_utils.read_global_cert_bundle()
        self.dispatcher.set_global_repo_auth(cds, bundle)

        # If the CDS should sync regularly, update that now
        if sync_schedule is not None:
            update_cds_schedule(cds, sync_schedule)

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

        try:
            self.dispatcher.release_cds(doomed)
        except CdsTimeoutException:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise PulpException('Timeout occurred attempting to release CDS [%s]' % hostname), None, exc_traceback
        except CdsCommunicationsException:
            log.exception('Communications exception occurred releasing CDS [%s]' % hostname)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise PulpException('Communications error while attempting to release CDS [%s]; check the server log for more information' % hostname), None, exc_traceback
        except CdsAuthException:
            log.exception('Authorization exception occurred releasing CDS [%s]' % hostname)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise PulpException('Communications error while attempting to release CDS [%s]; check the server log for more information' % hostname), None, exc_traceback
        except CdsMethodException:
            log.exception('CDS error encountered while attempting to releasing CDS [%s]' % hostname)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise PulpException('CDS error encountered while attempting to release CDS [%s]; check the server log for more information' % hostname), None, exc_traceback

        self.cds_history_api.cds_unregistered(hostname)

        # No need to send anything related to global repo auth; the CDS should
        # take care of deleting it from release call

        # If the CDS is scheduled to sync, remove that now
        delete_cds_schedule(doomed)

        # The above schedule delete call will update the DB, so this remove has to
        # occur after that
        self.collection.remove({'hostname' : hostname}, safe=True)
        
    def cds(self, hostname):
        '''
        Returns the CDS instance that has the given hostname if one exists.

        @param hostname: fully qualified hostname of the CDS instance
        @type  hostname: string

        @return: CDS instance if one exists with the exact hostname given; None otherwise
        @rtype:  L{pulp.server.db.model.CDS} or None
        '''
        matching_cds = list(self.collection.find(spec={'hostname': hostname}))
        if len(matching_cds) == 0:
            return None
        else:
            return matching_cds[0]

    def cds_with_repo(self, repo_id):
        '''
        Returns a list of all CDS instances that are associated with the given repo.

        @param repo_id: identifies the repo to search for associations; if this does not
                        represent a valid repo it will be treated as if there were no matching
                        results
        @type  repo_id: string

        @return: list of all matching CDS instances if any match; empty list otherwise
        @rtype:  list of L{CDS} instances
        '''
        cursor = self.collection.find({'repo_ids' : repo_id})
        return list(cursor)

    def list(self):
        '''
        Lists all CDS instances.

        @return: list of all registered CDS instances; empty list if none are registered
        @rtype:  list
        '''
        return list(self.collection.find())

    @audit()
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

        repo = self._repocollection().find_one({'id' : repo_id})
        if repo is None:
            raise PulpException('Repository with ID [%s] could not be found' % repo_id)

        # If the repo isn't already associated with the CDS, process it
        if repo_id not in cds['repo_ids']:

            # Update the CDS in the database
            cds['repo_ids'].append(repo_id)
            self.collection.save(cds, safe=True)

            # Add a history entry for the change
            self.cds_history_api.repo_associated(cds_hostname, repo_id)

            # If the repo has auth credentials, send them to the CDS
            repo_cert_utils = RepoCertUtils(config.config)
            bundle = repo_cert_utils.read_consumer_cert_bundle(repo_id)
            if bundle is not None:
                self.dispatcher.set_repo_auth(cds, repo_id, repo['relative_path'], bundle)

            # Add it to the CDS host assignment algorithm
            round_robin.add_cds_repo_association(cds_hostname, repo_id)

            # Automatically redistribute consumers to pick up these changes
            self.redistribute(repo_id)

    @audit()
    def unassociate_repo(self, cds_hostname, repo_id, deleted=False):
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

        @param deleted: Indicates the repo has been deleted.
        @type deleted: bool

        @raise PulpException: if the CDS does not exist
        '''

        # Entity load and sanity check on the arguments
        cds = self.cds(cds_hostname)
        if cds is None:
            raise PulpException('CDS with hostname [%s] could not be found' % cds_hostname)

        # If the repo is associated, process it
        if repo_id in cds['repo_ids']:

            # Update the CDS in the database
            cds['repo_ids'].remove(repo_id)
            self.collection.save(cds, safe=True)

            # Remove it from CDS host assignment consideration
            round_robin.remove_cds_repo_association(cds_hostname, repo_id)

            # Add a history entry for the change
            self.cds_history_api.repo_unassociated(cds_hostname, repo_id)

            # If the repo has auth credentials, tell the CDS to remove it from its
            # protected repo list
            repo_cert_utils = RepoCertUtils(config.config)
            bundle = repo_cert_utils.read_consumer_cert_bundle(repo_id)
            if bundle is not None:
                repo = Repo.get_collection().find_one({'id' : repo_id})
                self.dispatcher.set_repo_auth(cds, repo_id, repo['relative_path'], None)

            if not deleted:
                # Automatically redistribute consumers to pick up these changes
                self.redistribute(repo_id)

    def cds_sync(self, cds_hostname):
        '''
        Causes a CDS to be triggered to synchronize all of its repos as soon as possible,
        regardless of when its next scheduled sync would be. The CDS will be brought up to
        speed with all repos it is currently associated with, including deleting repos that
        are no longer associated with the CDS.

        This call is synchronous and potentially long running. Any threading of this call
        must already be in place.

        @param cds_hostname: identifies the CDS
        @type  cds_hostname: string; may not be None

        @raise PulpException: if the CDS does not exist
        '''
        log.info('Synchronizing CDS [%s]' % cds_hostname)

        # Entity load and sanity check on the arguments
        cds = self.cds(cds_hostname)
        if cds is None:
            raise PulpException('CDS with hostname [%s] could not be found' % cds_hostname)

        # Load the repo objects to send to the CDS with the call
        repos = []
        for repo_id in cds['repo_ids']:
            repo = self._repocollection().find_one({'id' : repo_id}, fields=REPO_FIELDS)
            repos.append(repo)

        # Call out to dispatcher to trigger sync, adding the appropriate history entries
        self.cds_history_api.sync_started(cds_hostname)

        # Catch any exception so thed sync_finished call is still made; can't add a
        # finally block when an except is in place in python 2.4, otherwise this would
        # be simpler.
        sync_error_msg = None
        sync_traceback = None
        try:
            self.dispatcher.sync(cds, repos)
        except CdsTimeoutException:
            log.exception('Timeout occurred during sync to CDS [%s]' % cds_hostname)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sync_traceback = exc_traceback
            sync_error_msg = 'Timeout occurred during sync'
        except CdsCommunicationsException:
            log.exception('Communications error during sync to CDS [%s]' % cds_hostname)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sync_traceback = exc_traceback
            sync_error_msg = 'Unknown communications error during sync'
        except CdsAuthException:
            log.exception('Authorization error during sync to CDS [%s]' % cds_hostname)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sync_traceback = exc_traceback
            sync_error_msg = 'Unknown authorization error during sync'
        except CdsMethodException:
            log.exception('CDS threw an error during sync to CDS [%s]' % cds_hostname)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sync_traceback = exc_traceback
            sync_error_msg = 'Error on the CDS during sync'
        except Exception:
            log.exception('Non-CdsDispatcherException error caught on sync invocation for CDS [%s]' % cds['hostname'])
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sync_traceback = exc_traceback
            sync_error_msg = 'Unknown error during sync'

        self.cds_history_api.sync_finished(cds_hostname, error=sync_error_msg)

        # Update the CDS to indicate the last sync time
        cds['last_sync'] = datetime.datetime.now().strftime('%s')
        self.collection.save(cds, safe=True)

        # Make sure the caller gets the error like normal (after the event logging) if
        # one occurred
        if sync_error_msg is not None:
            raise PulpException('%s; check the server log for more information' % sync_error_msg), None, sync_traceback

    def redistribute(self, repo_id):
        '''
        Triggers a recalculation of host URLs for the given repo for each consumer bound to
        it. The consumers will be sent a bind request with the updated host URL list.

        If there are no CDS associations for the given repo, this method has no effect.

        @param repo_id: identifies the repo whose host URLs will be recalculated
        @type  repo_id: string
        '''

        # Redistribute only applies if there are CDSes hosting the repo, so punch out early
        # if the iterator doesn't have anything
        iterator = round_robin.iterator(repo_id)
        if iterator is None:
            return

        # Punch out early if there are no bound consumers; there's nothing to do
        consumers = consumer_utils.consumers_bound_to_repo(repo_id)
        if len(consumers) == 0:
            return

        # Load the repo data
        repo = list(Repo.get_collection().find({'id' : repo_id}))[0]

        for consumer in consumers:

            # Get the next sequence to hand to this consumer
            hostnames = iterator.next()

            # Recreate the bind data since it is scoped to a particular consumer
            bind_data = consumer_utils.build_bind_data(repo, hostnames, None)

            # Blank the repo since nothing has changed in it, only the host/key URLs
            bind_data['repo'] = None
            bind_data['gpg_keys'] = None

            # Retrieve the repo proxy for the consumer being handled
            agent_repolib = pulp.server.agent.retrieve_repo_proxy(consumer['id'], async=True)

            # Send the update message to the consumer
            agent_repolib.update(repo_id, bind_data)

    def unassociate_all_from_repo(self, repo_id, deleted=False):
        '''
        Unassociates all CDS instances that are associated with the given repo. This is
        meant to be called in response to a repo being deleted. Unlike the unassociate call
        that requires an explicit sync, this call will trigger a message to be sent to each
        CDS to remove the repo. The rationale is that if a repo is deleted, we want it to
        be deleted everywhere as soon as possible without having to make the user explicitly
        trigger syncs on all CDS instances that may have the repo.
        @param repo_id: The ID of repo to unassociate with.
        @type repo_id: str
        @param deleted: Indicates the repo has been deleted.
        @type deleted: bool.
        @return: The list of hostnames successfully unassocated and a list of
            hostnames that failed to be unassociated.
        @rtype: tuple
        '''
        # Find all CDS instances associated with the given repo
        succeeded = []
        failed = []
        for cds in self.cds_with_repo(repo_id):
            hostname = cds['hostname']
            try:
                self.unassociate_repo(hostname, repo_id, deleted)
                succeeded.append(hostname)
            except Exception:
                failed.append(hostname)
                log.error('unassociate %s, failed', hostname, exc_info=True)
        return (succeeded, failed)

# -- internal only api ---------------------------------------------------------------------

    def set_global_repo_auth(self, cert_bundle):
        '''
        Notifies *all* CDS instances that global repo authentication has been changed
        on the Pulp server. If the bundle is None, the effect is that global repo
        authentication will be disabled.

        @param cert_bundle: contains the bundle contents (PEM encoded certificates and
                            keys); may be None
        @type  cert_bundle: dict {str, str} (see repo_cert_utils for more information)
        '''
        collection = CDS.get_collection()
        all_cds = list(collection.find())

        # Attempt to send to all CDS instances. For any that throw an error, log the
        # exception and keep a running track of which failed to display to the caller
        success_cds_hostnames = []
        error_cds_hostnames = []
        for cds in all_cds:
            try:
                self.dispatcher.set_global_repo_auth(cds, cert_bundle)
                success_cds_hostnames.append(cds['hostname'])
            except Exception:
                log.exception('Error enabling global repo auth on CDS [%s]' % cds['hostname'])
                error_cds_hostnames.append(cds['hostname'])

        return success_cds_hostnames, error_cds_hostnames

    def set_repo_auth(self, repo_id, repo_relative_path, cert_bundle):
        '''
        Notifies all CDS instances associated with the given repo that repo authentication
        has been changed. If the bundle is None, authentication for this repo will be
        removed.
        '''

        # Find all CDS instances associated with the given repo
        cds_list = self.cds_with_repo(repo_id)

        # Attempt to send to all CDS instances. For any that throw an error, log the
        # exception and keep a running track of which failed to display to the caller
        success_cds_hostnames = []
        error_cds_hostnames = []
        for cds in cds_list:
            try:
                self.dispatcher.set_repo_auth(cds, repo_id, repo_relative_path, cert_bundle)
                success_cds_hostnames.append(cds['hostname'])
            except Exception:
                log.exception('Error enabling repo auth on CDS [%s]' % cds['hostname'])
                error_cds_hostnames.append(cds['hostname'])

        return success_cds_hostnames, error_cds_hostnames
