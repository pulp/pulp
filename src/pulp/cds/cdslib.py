# Copyright (c) 2011 Red Hat, Inc.
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
import os
import sys
import logging
import shutil

# Pulp
from grinder.RepoFetch import YumRepoGrinder
from pulp.cds.lb.storage import FilePermutationStore
from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.repo_auth.protected_repo_utils import ProtectedRepoUtils

# -- constants ---------------------------------------------------------------

LOGPATH = '/var/log/pulp-cds/gofer.log'
REPO_LIST_FILENAME = '.cds_repo_list'
TIME = '%(asctime)s'
LEVEL = ' [%(levelname)s]'
THREAD = '[%(threadName)s]'
FUNCTION = ' %(funcName)s()'
FILE = ' @ %(filename)s'
LINE = ':%(lineno)d'
MSG = ' - %(message)s'

if sys.version_info < (2,5):
    FUNCTION = ''

FMT = \
    ''.join((TIME,
            LEVEL,
            THREAD,
            FUNCTION,
            FILE,
            LINE,
            MSG,))

log = None

# -- public ------------------------------------------------------------------

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
        handler = logging.FileHandler(path)
        handler.setFormatter(logging.Formatter(FMT))
        log.addHandler(handler)
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
        self._delete_all_repos()
        self.update_cluster_membership(None, None)

    def sync(self, sync_data):
        '''
        Synchronizes the given repos to this CDS. This list is the definitive list of what
        should be present on the CDS if this call succeeds. That includes removing any
        repos that were previously synchronized but are no longer in the given list of repos.

        @param sync_data: package of all data the CDS needs to configure itself, including
                          repo information and redundent cluster membership information;
                          see the CDS API for information on what is contained
        @type  sync_data: dict
        '''

        log.info('Received sync call')
        log.info(sync_data)

        error_messages = [] # keeps a running total of errors encountered to send back to the server

        # Unpack the necessary data
        repos = sync_data['repos']
        base_url = sync_data['repo_base_url']
        repo_cert_bundles = sync_data['repo_cert_bundles']
        global_cert_bundle = sync_data['global_cert_bundle']
        cluster_id = sync_data['cluster_id']
        cluster_members = sync_data['cluster_members']
        ca_cert_pem = sync_data['server_ca_cert']

        packages_location = self.config.get('cds', 'packages_dir')

        # Update the repo certificate bundles
        for repo in repos:
            bundle = repo_cert_bundles[repo['id']]

            try:
                self._set_repo_auth(repo['id'], repo['relative_path'], bundle)
            except Exception:
                log.exception('Error updating certificate bundle for repo [%s]' % repo['id'])
                error_messages.append('Error updating certificate bundle for repo [%s]' % repo['id'])

        # Update the CA certificate for the server
        ca_filename = self.config.get('server', 'ca_cert_file')
        try:
            if ca_cert_pem is None:
                if os.path.exists(ca_filename):
                    os.remove(ca_filename)
            else:
                f = open(ca_filename, 'w')
                f.write(ca_cert_pem)
                f.close()
        except Exception:
            log.exception('Error updating server CA certificate at [%s]' % ca_filename)
            error_messages.append('Error updating server CA certificate at [%s]' % ca_filename)

        # Update the global certificate bundle
        try:
            self._set_global_repo_auth(global_cert_bundle)
        except Exception:
            log.exception('Error updating global cert bundle')
            error_messages.append('Error updating global certificate bundle')

        # Clean up any repos that were once synchronized but are no longer associated with the CDS
        try:
            self._delete_removed_repos(repos)
        except Exception:
            log.exception('Error performing old repo cleanup')
            error_messages.append('One or more previously synchronized repositories could not be deleted')

        # Sync each repo specified, allowing the syncs to proceed if one or more fails
        successfully_syncced_repos = []
        for repo in repos:
            try:
                self._sync_repo(base_url, repo)
                successfully_syncced_repos.append(repo)
            except Exception:
                log.exception('Error performing repo sync')
                error_messages.append('Error synchronizing repository [%s]' % repo['id'])

            # Write it out per repo in case something drastically awful happens
            # so we have a best effort record

            # The only potential wonkiness is if the sync failed because the packages
            # location is unwritable, in which case this will fail too. That's fine,
            # since not having the file will mean no syncced repos and if we can't
            # write to the packages location, there's a solid chance we don't in fact
            # have any repos.
            repos_file = open(os.path.join(packages_location, REPO_LIST_FILENAME), 'w')
            for r in successfully_syncced_repos:
                repos_file.write(os.path.join('repos', r['relative_path']))
                repos_file.write('\n')
            repos_file.close()

        # If no repos were specified, make sure the CDS repo list file does not
        # contain references to any CDS instances
        if len(repos) == 0:
            repos_file = open(os.path.join(packages_location, REPO_LIST_FILENAME), 'w')
            repos_file.write('')
            repos_file.close()

        # Make sure the CDS cluster list is up to speed
        try:
            self.update_cluster_membership(cluster_id, cluster_members)
        except Exception:
            log.exception('Error updating cluster membership')
            error_messages.append('Error updating cluster membership')

        if len(error_messages) > 0:
            raise Exception('The following errors occurred during the CDS sync: ' + ', '.join(error_messages))

    def update_cluster_membership(self, cluster_name, cds_hostnames):
        '''
        Updates the local knowledge of this CDS instance's cluster membership
        and other CDS instances in the same cluster.

        If cluster_name is None, the effect is that this CDS has been removed
        from a cluster.

        If the cluster membership has not changed, no changes are made.

        @param cluster_name: identifies the cluster the CDS is a member in
        @type  cluster_name: str or None

        @param cds_hostnames: list of all CDS instances in the cluster (this instance
                              will be listed in this list as well)
        @type  cds_hostnames: list of str
        '''
        if cds_hostnames is None:
            cds_hostnames = []
            
        members = ', '.join(cds_hostnames)
        log.info('Received cluster membership update; Cluster [%s], Members [%s]' % (cluster_name, members))

        file_storage = FilePermutationStore()
        file_storage.open()

        try:
            # Only edit if there were changes to the CDS cluster
            if sorted(file_storage.permutation) != sorted(cds_hostnames):
                file_storage.permutation = cds_hostnames
                file_storage.save()
            else:
                log.info('No changes needed to be made to cluster memberships')
        finally:
            file_storage.close()

    # -- internal ------------------------------------------------------------

    def _set_repo_auth(self, repo_id, repo_relative_path, bundle):
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

    def _set_global_repo_auth(self, bundle):
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

    def _sync_repo(self, base_url, repo):
        '''
        Synchronizes a repository from the Pulp server.

        @param base_url: location of the base URL where repos are hosted, the url
                         should end in a trailing / but is not required to;
                         example: https://pulp.example.com/
        @type  base_url: string

        @param repo: contains the details of the repository to sync
        @type  repo: dict of str
        '''

        num_threads = self.config.get('cds', 'sync_threads')
        content_base = self.config.get('cds', 'packages_dir')
        packages_dir = os.path.join(content_base, 'packages')

        url = '%s/%s' % (base_url, repo['relative_path'])
        log.info('Synchronizing repo at [%s]' % url)
        repo_path = os.path.join(content_base, 'repos', repo['relative_path'])

        if not os.path.exists(repo_path):
            os.makedirs(repo_path)

        log.info('Synchronizing repo [%s] from [%s] to [%s]' % (repo['name'], url, repo_path))

        # If the repo is protected, add in the credentials
        feed_ca = feed_cert = None
        ssl_verify = 0
        bundle = self.repo_cert_utils.consumer_cert_bundle_filenames(repo['id'])
        if bundle is not None:
            log.debug('Configuring repository for authentication')
            server_ca_filename = self.config.get('server', 'ca_cert_file').encode('utf8')
            if os.path.exists(server_ca_filename):
                feed_ca = server_ca_filename
            else:
                feed_ca = bundle['ca'].encode('utf8')
            feed_cert = bundle['cert'].encode('utf8')
            ssl_verify = 1

        # If the repo itself wasn't protected but there is global repo auth, use that
        if bundle is None:
            bundle = self.repo_cert_utils.global_cert_bundle_filenames()
            if bundle is not None:
                log.debug('Configuring global repository authentication credentials for repo')
                server_ca_filename = self.config.get('server', 'ca_cert_file').encode('utf8')
                if os.path.exists(server_ca_filename):
                    feed_ca = server_ca_filename
                else:
                    feed_ca = bundle['ca'].encode('utf8')
                feed_cert = bundle['cert'].encode('utf8')
                ssl_verify = 1
        
        verify_options = {}
        verify_options["size"] = self.config.getboolean('cds', "verify_size")
        verify_options["checksum"] = self.config.getboolean('cds', "verify_checksum")
        fetch = YumRepoGrinder('', url, num_threads, sslverify=ssl_verify,
                               cacert=feed_ca, clicert=feed_cert,
                               packages_location=packages_dir)
        fetch.fetchYumRepo(repo_path, verify_options=verify_options)

        log.info('Successfully finished synccing [%s]' % url)

    def _delete_removed_repos(self, repos):
        '''
        Deletes any repos that were synchronized in a previous sync but have since been
        unassociated from the CDS. This will *not* affect the local listings file;
        it's assumed that task will be taken care of elsewhere.

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
        repo_list_contents = repo_list_file.read()
        repo_list_file.close()

        existing_repo_relative_urls = repo_list_contents.split()

        # Transform the list of repo dicts into just a list of relative URLs; this will
        # make the existence of a repo checking much simpler.
        # Prefix the URL with repos since locally the relative URLs are prefixed
        # with it.
        sync_repo_relative_urls = [os.path.join('repos', r['relative_path']) for r in repos]

        # Determine the repos that are no longer supposed to be syncced
        delete_us_relative_urls = [r for r in existing_repo_relative_urls if r not in sync_repo_relative_urls]

        # Delete the local paths and protection for those repos
        for relative_path in delete_us_relative_urls:
            doomed = os.path.join(packages_dir, relative_path)
            log.info('Removing old repo [%s]' % doomed)

            if os.path.exists(doomed):
                shutil.rmtree(doomed)
            else:
                log.warn('Repository at [%s] could not be found for deletion' % doomed)

            self.protected_repo_utils.delete_protected_repo(relative_path)

    def _delete_all_repos(self):
        '''
        Cleanup function used when a CDS is unregistered to remove all of its repositories.
        '''

        # Load the list of all currently syncced repos. If this can't be loaded, there
        # isn't anything that can be done in terms of deleting old repos, so punch out early.        
        packages_dir = self.config.get('cds', 'packages_dir')
        repo_list_filename = os.path.join(packages_dir, REPO_LIST_FILENAME)
        if not os.path.exists(repo_list_filename):
            return

        repo_list_file = open(repo_list_filename, 'r')
        repo_paths = repo_list_file.read().split()

        # Delete the local paths for those urls
        for path in repo_paths:
            doomed = os.path.join(packages_dir, path)
            log.info('Removing old repo [%s]' % doomed)

            if os.path.exists(doomed):
                shutil.rmtree(doomed)
            else:
                log.warn('Repository at [%s] could not be found for deletion' % doomed)

        # Clear the repos listing
        packages_location = self.config.get('cds', 'packages_dir')
        repos_file = open(os.path.join(packages_location, REPO_LIST_FILENAME), 'w')
        repos_file.write('')
        repos_file.close()


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
