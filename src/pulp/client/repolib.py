# Copyright (c) 2011 Red Hat, Inc.
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

'''
Logic methods for handling repo bind, unbind, and update operations. This module
is independent of how the requests for these operations are received. In other words,
this module does not care if the required information for these commands is received
through API calls or the message bus. The logic is still the same and occurs
entirely on the consumer.
'''

# Python
import os

# Pulp
from pulp.client.lock import Lock
from pulp.client.logutil import getLogger
from pulp.client.repo_file import Repo, RepoFile, MirrorListFile

log = getLogger(__name__)

# -- constants ----------------------------------------------------------------

# Create a single lock at the module level that will be used for all invocations.
# It can be overridden in the public methods if necessary.
REPO_LOCK = Lock('/var/run/subsys/pulp/repolib.pid')

# -- public ----------------------------------------------------------------

def bind(repo_filename, mirror_list_filename, repo_data, url_list, lock=REPO_LOCK):
    '''
    Uses the given data to safely bind a repo to a repo file. This call will
    determine the best method for representing the repo given the data in the
    repo object as well as the list of URLs where the repo can be found.

    This call may be used to bind a new repo or update the details of a previously
    bound repo.

    The default lock is defined at the module level and is
    used to ensure that concurrent access to the give files is prevented. Specific
    locks can be passed in for testing purposes to circumvent the default
    location of the lock which requires root access.

    @param repo_filename: full path to the location of the repo file in which
                          the repo will be bound; this file does not need to
                          exist prior to this call
    @type  repo_filename: string

    @param mirror_list_filename: full path to the location of the mirror list file
                                 that should be written for the given repo if
                                 necessary; this should be unique for the given repo
    @type  mirror_list_filename: string

    @param repo_data: contains data on the repo being bound
    @type  repo_data: dict

    @param url_list: list of URLs that will be used to access the repo; this call
                     will determine the best way to represent the URL list in
                     the repo definition
    @type  url_list: list

    @param lock: if the default lock is unacceptble, it may be overridden in this variable
    @type  lock: L{Lock}
    '''

    lock.acquire()
    try:
        log.info('Binding repo [%s]' % repo_data['id'])

        repo_file = RepoFile(repo_filename)
        repo_file.load()
        
        repo = _convert_repo(repo_data)

        if len(url_list) > 1:

            # The mirror list file isn't loaded; if this call was made as part of a
            # repo update the file should be written new given the URLs passed in
            mirror_list_file = MirrorListFile(mirror_list_filename)
            mirror_list_file.add_entries(url_list)
            mirror_list_file.save()
            
            repo['mirrorlist'] = mirror_list_filename

            log.info('Created mirrorlist for repo [%s] at [%s]' % (repo.id, mirror_list_filename))
        else:

            # On a repo update, the mirror list may have existed but is no longer used.
            # If we're in this block there shouldn't be a mirror list file for the repo,
            # so delete it if it's there.
            if os.path.exists(mirror_list_filename):
                os.remove(mirror_list_filename)

            repo['baseurl'] = url_list[0]
            log.info('Configuring repo [%s] to use baseurl [%s]' % (repo.id, url_list[0]))

        if repo_file.get_repo(repo.id):
            log.info('Updating repo [%s]' % repo.id)
            repo_file.update_repo(repo)
        else:
            log.info('Adding new repo [%s]' % repo.id)
            repo_file.add_repo(repo)
            
        repo_file.save()
    finally:
        lock.release()

def unbind(repo_filename, mirror_list_filename, repo_id, lock=REPO_LOCK):
    '''
    Removes the repo identified by repo_id from the given repo file. If the repo is
    not bound, this call has no effect. If the mirror list file exists, it will be
    deleted.

    The default lock is defined at the module level and is
    used to ensure that concurrent access to the give files is prevented. Specific
    locks can be passed in for testing purposes to circumvent the default
    location of the lock which requires root access.

    @param repo_filename: full path to the location of the repo file in which
                          the repo will be removed; if this file does not exist
                          this call has no effect
    @type  repo_filename: string

    @param mirror_list_filename: full path to the location of the mirror list file
                                 that may exist for the given repo; if the file does
                                 not exist this field will be ignored
    @type  mirror_list_filename: string

    @param repo_id: identifies the repo in the repo file to delete
    @type  repo_id: string

    @param lock: if the default lock is unacceptble, it may be overridden in this variable
    @type  lock: L{Lock}
    '''

    lock.acquire()
    try:
        log.info('Unbinding repo [%s]' % repo_id)

        if not os.path.exists(repo_filename):
            return

        repo_file = RepoFile(repo_filename)
        repo_file.load()
        repo_file.remove_repo_by_name(repo_id) # will not throw an error if repo doesn't exist
        repo_file.save()

        if os.path.exists(mirror_list_filename):
            os.remove(mirror_list_filename)
    finally:
        lock.release()

# -- private -----------------------------------------------------------------

def _convert_repo(repo_data):
    '''
    Converts the dict repository representation into the repo file domain instance.
    This will *not* populate the baseurl parameter of the repo. That will be done
    elsewhere to take into account if a mirror list is required depending on the
    host URLs sent with the bind response.

    @param repo: contains data for the repo to be created
    @type  repo: dict

    @return: repo instance in the repo file format
    @rtype:  L{Repo}
    '''
    repo = Repo(str(repo_data['id']))
    repo['name'] = repo_data['name']
    repo['gpgcheck'] = '0'

    # This probably won't be an issue; you shouldn't be able to bind to an unpublished repo
    if bool(repo_data['publish']):
        enabled = '1'
    else:
        enabled = '0'

    repo['enabled'] = enabled

    return repo
