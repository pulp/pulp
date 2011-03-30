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
import os
import logging
import shutil

# Pulp
from grinder.RepoFetch import YumRepoGrinder
from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.repo_auth.protected_repo_utils import ProtectedRepoUtils


LOGPATH = '/var/log/pulp-cds/gofer.log'
REPO_LIST_FILENAME = 'cds_repo_list'

log = None


def loginit(path=LOGPATH):
    '''
    Init log if (once).
    @param path: The absolute path to the log file.
    @type path: str
    @return: The logger.
    @rtype: Logger
    '''
    global log
    if log is None:
        logdir = os.path.dirname(path)
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        log = logging.getLogger(__name__)
        log.addHandler(logging.FileHandler(path))
        log.setLevel(logging.DEBUG)
    return log

class CdsLib(object):

    def __init__(self, config):
        '''
        Init logging.
        @param config: The CDS configuration.
        @type config: SafeConfigParser
        '''
        self.config = config
        self.repo_cert_utils = RepoCertUtils(self.config)
        self.protected_repo_utils = ProtectedRepoUtils(self.config)
        
        loginit()

    def initialize(self):
        '''
        Performs any initialization needed when a pulp server registered this CDS.

        Currently, this is simply a logging operation to keep record of the fact. It
        is also used as a ping mechanism to make sure the CDS is running before pulp
        acknowledges it was successfully registered.
        '''
        log.info('Received initialize call')

    def release(self):
        '''
        Release the CDS. Clear the shared secret and any global repo auth credentials
        it has.
        '''
        log.info('Received release call')

        self.repo_cert_utils.delete_global_cert_bundle()

        # TODO: this should probably clean up all repos as well

    def sync(self, base_url, repos):
        '''
        Synchronizes the given repos to this CDS. This list is the definitive list of what
        should be present on the CDS if this call succeeds. That includes removing any
        repos that were previously synchronized but are no longer in the given list of repos.

        @param base_url: location of the base URL where repos are hosted, the url
                         should end in a trailing / but is not required to;
                         example: https://pulp.example.com/
        @type  base_url: string

        @param repos: list of repos that should be on the CDS following synchronization
        @type  repos: list of dict, where each dict describes a repo that should be present
                      on the CDS
        '''

        log.info('Received sync call')
        log.info(repos)

        # This call simply wraps the actual logic so that any errors that occur are logged
        # on the CDS itself before they are re-raised to the pulp server.
        try:
            self._delete_removed_repos(repos)
            self._sync_repos(base_url, repos)
        except Exception, e:
            log.exception('Error performing sync')
            raise e

    def set_repo_auth(self, repo_id, repo_relative_path, bundle):
        '''
        Saves repo authentication credentials for a repo. If the credentials are None,
        the repo will be removed from the protected repo list.

        In the case that a repo with credentials has its relative path updated, two
        calls to this will be made by the server. The first will be with the old
        relative path and empty credentials, meant to remove the old listing from the
        protected repo list. The second will be a new entry with the credentials
        set against the new relative path.

        @param repo_id: identifies the repo; this is used for the storage and retrieval
                        of the credentials
        @type  repo_id: str

        @param repo_relative_path: used in mapping the request URL to the repo credentials
        @type  repo_relative_path: str

        @param bundle: the certificate bundle containing the pieces necessary for auth
        @param bundle: dict {str, str}
        '''

        # If the items in bundle have None values, the following call will delete the
        # associated file if one exists. If the bundle is None, all related cert bundle
        # files will be deleted.
        self.repo_cert_utils.write_consumer_cert_bundle(repo_id, bundle)

        # Determine whether or not to add the repo
        if bundle is None:
            self.protected_repo_utils.delete_protected_repo(repo_relative_path)
        else:
            self.protected_repo_utils.add_protected_repo(repo_relative_path, repo_id)

    def set_global_repo_auth(self, bundle):
        '''
        Saves the global repo auth credentials which are applied to all repo
        accesses. If the credentials are None, the global credentials will be removed.

        @param bundle: the certificate bundle containing the pieces necessary for auth
        @param bundle: dict {str, str}
        '''

        # If the items in bundle have None values, the following call will delete the
        # associated file if one exists. If the bundle is None, all related cert bundle
        # files will be deleted.
        self.repo_cert_utils.write_global_repo_cert_bundle(bundle)

    def _sync_repos(self, base_url, repos):
        '''
        Synchronizes all repos specified in the sync call.

        @param base_url: location of the base URL where repos are hosted, the url
                         should end in a trailing / but is not required to;
                         example: https://pulp.example.com/
        @type  base_url: string

        @param repos: list of repos that should be on the CDS following synchronization
        @type  repos: list of dict, where each dict describes a repo that should be present
                      on the CDS
        '''

        num_threads = self.config.get('cds', 'sync_threads')
        packages_location = self.config.get('cds', 'packages_dir')

        # Keep a running total of all repos that have been successfully synchronized so
        # we can write out the list
        successfully_syncced_repos = []

        # Synchronize all repos that were specified
        for repo in repos:

            try:
                url = '%s/%s' % (base_url, repo['relative_path'])
                log.debug('Synchronizing repo at [%s]' % url)
                repo_path = os.path.join(packages_location, repo['relative_path'])

                if not os.path.exists(repo_path):
                    os.makedirs(repo_path)

                log.debug('Synchronizing repo [%s] from [%s] to [%s]' % (repo['name'], url, repo_path))

                fetch = YumRepoGrinder('', url, num_threads, sslverify=0)
                fetch.fetchYumRepo(repo_path)

                successfully_syncced_repos.append(repo)
            finally:
                # Write it out after each repo so that even if a single repo throws an error
                # on sync, the written file will still be accurate.

                # The only potential wonkiness is if the sync failed because the packages
                # location is unwritable, in which case this will fail too. That's fine,
                # since not having the file will mean no syncced repos and if we can't
                # write to the packages location, there's a solid chance we don't in fact
                # have any repos.
                repos_file = open(os.path.join(packages_location, REPO_LIST_FILENAME), 'w')
                for r in successfully_syncced_repos:
                    repos_file.write(r['relative_path'])
                    repos_file.write('\n')
                repos_file.close()

    def _delete_removed_repos(self, repos):
        '''
        Deletes any repos that were synchronized in a previous sync but have since been
        unassociated from the CDS.

        @param repos: list of repos that should be on the CDS following synchronization;
                      any repos that were synchronized previously but are no longer in
                      this list will be deleted by this call
        @type  repos: list of dict, where each dict describes a repo that should be present
                      on the CDS
        '''

        packages_dir = self.config.get('cds', 'packages_dir')

        # Load the list of all currently syncced repos. If this can't be loaded, there
        # isn't anything that can be done in terms of deleting old repos, so punch out early.
        repo_list_filename = os.path.join(packages_dir, REPO_LIST_FILENAME)
        if not os.path.exists(repo_list_filename):
            return

        repo_list_file = open(repo_list_filename, 'r')
        existing_repo_relative_urls = repo_list_file.read().split()

        # Transform the list of repo dicts into just a list of relative URLs; this will
        # make the existence of a repo checking much simpler.
        sync_repo_relative_urls = [r['relative_path'] for r in repos]

        # Determine the repos that are no longer supposed to be syncced
        delete_us_relative_urls = [r for r in existing_repo_relative_urls if r not in sync_repo_relative_urls]

        # Delete the local paths for those urls
        for relative_path in delete_us_relative_urls:
            doomed = os.path.join(packages_dir, relative_path)
            log.info('Removing old repo [%s]' % doomed)
            shutil.rmtree(doomed)


class SecretFile:
    '''
    Represents the persistent shared secret.
    '''

    def __init__(self, path):
        '''
        @param path: The absolute to the file where the secret
            is stored.  The directory is created automatically.
        @type path: str
        '''
        self.path = path
        self.__mkdir()

    def read(self):
        '''
        Read and return the stored secret.
        @return: The stored secret.
        @rtype: str
        '''
        if os.path.exists(self.path):
            f = open(self.path)
            secret = f.read()
            f.close()
            return secret

    def write(self, secret):
        '''
        Store the specified secret.
        @param secret: The secret to store.
        @type secret: str
        '''
        f = open(self.path, 'w')
        f.write(secret)
        f.close()
        return secret

    def delete(self):
        '''
        Delete the stored secret.
        '''
        if os.path.exists(self.path):
            os.unlink(self.path)

    def __mkdir(self):
        '''
        Ensure directory exists.
        '''
        path = os.path.dirname(self.path)
        if not os.path.exists(path):
            os.makedirs(path)
