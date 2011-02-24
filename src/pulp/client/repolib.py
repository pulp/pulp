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
#

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

# -- concurrency utilities ----------------------------------------------------------------

class ActionLock(Lock):
    """
    Action lock.
    @cvar PATH: The lock file absolute path.
    @type PATH: str
    """

    PATH = '/var/run/subsys/pulp/repolib.pid'

    def __init__(self, path=PATH):
        Lock.__init__(self, path)

# Create a single lock at the module level that will be used for all invocations.
# It can be overridden in the public methods if necessary.
REPO_LOCK = ActionLock()

# -- public ----------------------------------------------------------------

def bind(repo_filename, mirror_list_filename, repo, url_list, lock=REPO_LOCK):
    lock.acquire()
    try:
        repo_file = RepoFile(repo_filename)
        repo_file.load()
        
        repo = _convert_repo(repo)

        if len(url_list) > 1:
            mirror_list_file = MirrorListFile(mirror_list_filename)
            mirror_list_file.add_entries(url_list)
            mirror_list_file.save()
            
            repo['mirrorlist'] = mirror_list_filename
        else:
            repo['baseurl'] = url_list[0]

        repo_file.add_repo(repo)
        repo_file.save()
    finally:
        lock.release()

def unbind(repo_filename, mirror_list_filename, repo_id, lock=REPO_LOCK):
    lock.acquire()
    try:
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
