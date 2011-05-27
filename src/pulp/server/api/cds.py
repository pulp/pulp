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

# Python
import datetime
import logging
import re
import sys

# Pulp
from pulp.common import dateutils

from pulp.repo_auth.repo_cert_utils import RepoCertUtils

from pulp.server import config, constants, consumer_utils
from pulp.server.agent import PulpAgent
from pulp.server.api.base import BaseApi
from pulp.server.api.cds_history import CdsHistoryApi
from pulp.server.api.scheduled_sync import update_cds_schedule, delete_cds_schedule
from pulp.server.auditing import audit
from pulp.server.cds import round_robin
from pulp.server.cds.dispatcher import (
    GoferDispatcher, CdsTimeoutException, CdsCommunicationsException,
    CdsAuthException, CdsMethodException,)
from pulp.server.db.model import CDS, Repo
from pulp.server.pexceptions import PulpException

# -- constants ----------------------------------------------------------------

log = logging.getLogger(__name__)

GROUP_ID_PATTERN = re.compile(r'^[-_A-Za-z0-9]+$')

REPO_FIELDS = [
    'id',
    'source',
    'name',
    'arch',
    'relative_path',
    'publish',
]

# -- api ----------------------------------------------------------------------

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
    def register(self, hostname, name=None, description=None, sync_schedule=None, group_id=None):
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

        @param group_id: identifies the group the CDS belongs to
        @type  group_id: str

        @raise PulpException: if the CDS already exists, the hostname is unspecified, or
                              the CDS initialization fails
        '''
        if not hostname:
            raise PulpException('Hostname cannot be empty')

        if group_id is not None and GROUP_ID_PATTERN.match(group_id) is None:
            raise PulpException('Group ID must match the standard ID restrictions')

        existing_cds = self.cds(hostname)

        if existing_cds:
            raise PulpException('CDS already exists with hostname [%s]' % hostname)

        cds = CDS(hostname, name, description)
        cds.sync_schedule = sync_schedule
        cds.group_id = group_id

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

        # Group handling
        if group_id is not None:

            # Bring this CDS up to speed with any repo associations the others have
            self._apply_group_repos_to_cds(cds)

            # Notify other CDS instances
            self._update_group_membership(group_id)

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

        # If the CDS was part of a group, notify its remaining members of the change
        # (this has to happen after the DB update so the unregistered CDS does not
        # show up in the membership list)
        if doomed['group_id'] is not None:
            self._update_group_membership(doomed['group_id'])
        
    def update(self, hostname, delta):
        '''
        Updates values in an existing CDS. The following properties may be updated:
        - name
        - description
        - sync schedule
        - group membership

        @param hostname: identifies the CDS being updated
        @type  hostname: str

        @param delta: mapping of properties and values to change
        @type  delta: dict

        @raises PulpException: if any of the new values are invalid
        '''

        log.info('Updating CDS [%s]' % hostname)
        log.info(delta)

        # Validate ----------
        if 'sync_schedule' in delta and delta['sync_schedule'] is not None: # will be None if removing the schedule
            try:
                dateutils.parse_iso8601_interval(delta['sync_schedule'])
            except:
                log.exception('Could not update CDS [%s] because the sync schedule was invalid [%s]' % (hostname, delta['sync_schedule']))
                raise PulpException('Invalid sync schedule format [%s]' % delta['sync_schedule']), None, sys.exc_info()[2]

        if 'group_id' in delta and delta['group_id'] is not None: # will be None if removing the group
            if GROUP_ID_PATTERN.match(delta['group_id']) is None:
                log.info('Could not update CDS [%s] because the group ID was invalid [%s]' % (hostname, delta['group_id']))
                raise PulpException('Group ID must match the standard ID restrictions')

        # Update ----------
        cds = self.cds(hostname)

        # If we ever get enough values to warrant a loop, we can add it. For now, it's
        # just simpler to handle one at a time.
        if 'name' in delta:
            cds['name'] = delta['name']

        if 'description' in delta:
            cds['description'] = delta['description']
            
        if 'sync_schedule' in delta:
            cds['sync_schedule'] = delta['sync_schedule']

            if delta['sync_schedule'] is not None:
                update_cds_schedule(cds, delta['sync_schedule'])
            else:
                delete_cds_schedule(cds)

        if 'group_id' in delta:

            # There are three cases to handle in the case of a group ID change:
            # - CDS was not previously in a group and is added to one
            # - CDS was in a group and has been removed from it
            # - CDS was in a group and is now in a different group

            # Not previously in a group but now is
            if cds['group_id'] is None:
                log.info('Assigning previously ungrouped CDS [%s] to group [%s]' % (hostname, delta['group_id']))

                cds['group_id'] = delta['group_id']
                self.collection.save(cds, safe=True)

                self._update_group_membership(delta['group_id'])

                # The CDS is now part of a group, so make sure its repos are up to speed
                self._apply_group_repos_to_cds(cds)

            # CDS was in a group but no longer is
            elif cds['group_id'] is not None and delta['group_id'] is None:
                log.info('Removing CDS [%s] from group [%s]' % (hostname, cds['group_id']))

                old_group_id = cds['group_id']
                cds['group_id'] = None
                self.collection.save(cds, safe=True)

                # Notify the CDS it's not in a group
                try:
                    self.dispatcher.update_group_membership(cds, None, None)
                except Exception:
                    log.exception('Error notifying CDS [%s] it has been removed from group [%s]' % (hostname, old_group_id))

                self._update_group_membership(old_group_id)

            # CDS was in a group and is being changed
            elif cds['group_id'] != delta['group_id']:
                log.info('Changing CDS [%s] from group [%s] to group [%s]' % (hostname, cds['group_id'], delta['group_id']))

                old_group_id = cds['group_id']
                cds['group_id'] = delta['group_id']
                self.collection.save(cds, safe=True)

                self._update_group_membership(old_group_id)
                self._update_group_membership(delta['group_id'])

                # The CDS is now part of a different group, so make sure its repos are up to speed
                self._apply_group_repos_to_cds(cds)

        else:
            # If the group was changed, the CDS has already been saved. If not,
            # make sure to do it here.
            self.collection.save(cds, safe=True)
            
        return cds

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
    def associate_repo(self, cds_hostname, repo_id, apply_to_group=True):
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

        @param apply_to_group: if True, the association will be applied to all other CDS
                               instances in the same group; if False the group is ignored
        @type  apply_to_group: bool

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

            # Add it to the CDS host assignment algorithm
            round_robin.add_cds_repo_association(cds_hostname, repo_id)

            # Automatically redistribute consumers to pick up these changes
            self.redistribute(repo_id)

            # Make the same association on all other CDS instances in the group
            if cds['group_id'] is not None and apply_to_group:
                self._apply_cds_repos_to_group(cds)

    @audit()
    def unassociate_repo(self, cds_hostname, repo_id, deleted=False, apply_to_group=True):
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

        @param deleted: indicates the repo has been deleted.
        @type  deleted: bool

        @param apply_to_group: if True, the association will be applied to all other CDS
                       instances in the same group; if False the group is ignored
        @type  apply_to_group: bool

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

            # Automatically redistribute consumers to pick up these changes
            if not deleted:
                self.redistribute(repo_id)

            # Make the same unassociation on all other CDS instances in the group
            if cds['group_id'] is not None and apply_to_group:
                self._apply_cds_repos_to_group(cds)
            
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

        # -- assemble payload -----------------------------

        repo_cert_utils = RepoCertUtils(config.config)

        # Load the repo objects to send to the CDS with the call
        repos = []
        repo_cert_bundles = {}

        for repo_id in cds['repo_ids']:
            repo = self._repocollection().find_one({'id' : repo_id}, fields=REPO_FIELDS)

            # Load the repo cert bundle
            bundle = repo_cert_utils.read_consumer_cert_bundle(repo_id)
            repo_cert_bundles[repo['id']] = bundle

            repos.append(repo)

        # Repository base URL for this pulp server
        server_url = constants.SERVER_SCHEME + config.config.get('server', 'server_name')
        repo_relative_url = config.config.get('server', 'relative_url')
        repo_base_url = '%s/%s' % (server_url, repo_relative_url)

        # Global cert bundle, if any (repo cert bundles are handled above)
        global_cert_bundle = repo_cert_utils.global_cert_bundle_filenames()

        # Assemble the list of CDS hostnames in the same group
        if cds['group_id'] is not None:
            group_id = cds['group_id']
            cds_members = list(self.collection.find({'group_id' : cds['group_id']}))
            member_hostnames = [c['hostname'] for c in cds_members]
        else:
            group_id = None
            member_hostnames = None

        payload = {
            'repos'              : repos,
            'repo_base_url'      : repo_base_url,
            'repo_cert_bundles'  : repo_cert_bundles,
            'global_cert_bundle' : global_cert_bundle,
            'group_id'           : group_id,
            'group_members'      : member_hostnames,
        }

        # -- dispatch -------------------------------------

        # Call out to dispatcher to trigger sync, adding the appropriate history entries
        self.cds_history_api.sync_started(cds_hostname)

        # Catch any exception so thed sync_finished call is still made; can't add a
        # finally block when an except is in place in python 2.4, otherwise this would
        # be simpler.
        sync_error_msg = None
        sync_traceback = None
        try:
            self.dispatcher.sync(cds, payload)
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

        # -- tracking -------------------------------------

        self.cds_history_api.sync_finished(cds_hostname, error=sync_error_msg)

        # Update the CDS to indicate the last sync time
        now = datetime.datetime.now(dateutils.local_tz())
        cds['last_sync'] = dateutils.format_iso8601_datetime(now)
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
            agent = PulpAgent(consumer, async=True)
            agent_repolib = agent.Repo()

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
        '''
        for cds in self.cds_with_repo(repo_id):
            hostname = cds['hostname']
            try:
                self.unassociate_repo(hostname, repo_id, deleted)
            except Exception:
                log.error('unassociate %s, failed', hostname, exc_info=True)

# -- private -------------------------------------------------------------------------------

    def _update_group_membership(self, group_id):
        '''
        Notifies all CDS instances that are part of the given group that the membership
        in that group has changed. A list of all current members in the group is sent
        to each CDS in the group.

        @param group_id: identifies the group whose membership changed
        @type  group_id: str
        '''

        # Find all CDS instances in the group
        cds_members = list(self.collection.find({'group_id' : group_id}))

        member_hostnames = [c['hostname'] for c in cds_members]

        # Notify each one, keeping a running list of successes and failures
        success_cds_hostnames = []
        error_cds_hostnames = []

        for cds in cds_members:
            try:
                self.dispatcher.update_group_membership(cds, group_id, member_hostnames)
                success_cds_hostnames.append(cds['hostname'])
            except Exception:
                log.exception('Error notifying CDS [%s] of changes to group [%s]' % (cds['hostname'], group_id))
                error_cds_hostnames.append(cds['hostname'])

        return success_cds_hostnames, error_cds_hostnames
        
    def _apply_group_repos_to_cds(self, cds):
        """
        Run when a CDS is added to an existing group. If the group had other members
        before this CDS was added, the repo list from those instances will be associated
        with the newly added CDS.

        This call is meant to be called after the CDS has been successfully added to
        the group.

        @param cds: CDS that was newly added to the group
        @type  cds: L{CDS}
        """

        # This shouldn't happen, but safety check
        if cds['group_id'] is None:
            log.warn('Apply group repos to CDS called for CDS with no group [%s]' % cds['hostname'])
            return

        # All CDS instances in the group _except_ the one passed in
        cdses_in_group = list(self.collection.find({'group_id' : cds['group_id'], 'hostname' : {'$ne' : cds['hostname']}}))

        if len(cdses_in_group) == 0:
            return

        # They should all have the same repos, so just grab one as a sampling
        sample_cds = cdses_in_group[0]

        additions = [repo_id for repo_id in sample_cds['repo_ids'] if repo_id not in cds['repo_ids']]
        removals = [repo_id for repo_id in cds['repo_ids'] if repo_id not in sample_cds['repo_ids']]

        for repo_id in additions:
            self.associate_repo(cds['hostname'], repo_id, apply_to_group=False)

        for repo_id in removals:
            self.unassociate_repo(cds['hostname'], repo_id, apply_to_group=False)

    def _apply_cds_repos_to_group(self, cds):
        """
        Run when a CDS that is part of a group has its associated repos updated.
        This call will apply those changes to the other members in the group as well.
        """

        # This shouldn't happen, but safety check
        if cds['group_id'] is None:
            log.warn('Apply CDS repos to group called for CDS with no group [%s]' % cds['hostname'])
            return

        # The CDS specified now contains the most up to date list of repos, so
        # bring all other members of the group in line with that.
        
        # All CDS instances in the group _except_ the one passed in
        cdses_in_group = list(self.collection.find({'group_id' : cds['group_id'], 'hostname' : {'$ne' : cds['hostname']}}))

        for change_me in cdses_in_group:

            # Before editing the repo associations, determine additions/removals
            additions = [repo_id for repo_id in cds['repo_ids'] if repo_id not in change_me['repo_ids']]
            removals = [repo_id for repo_id in change_me['repo_ids'] if repo_id not in cds['repo_ids']]

            for repo_id in additions:
                self.associate_repo(change_me['hostname'], repo_id, apply_to_group=False)

            for repo_id in removals:
                self.unassociate_repo(change_me['hostname'], repo_id, apply_to_group=False)