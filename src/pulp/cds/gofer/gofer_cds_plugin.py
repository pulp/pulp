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
import os
import shutil
import socket

# 3rd Party
from gofer.agent.plugin import Plugin
from gofer.decorators import remote, identity
from grinder.RepoFetch import YumRepoGrinder


log = logging.getLogger(__name__)
log.addHandler(logging.FileHandler('/var/log/pulp-cds/gofer.log'))
log.setLevel(logging.DEBUG)
log.info('CDS gofer plugin initialized')

plugin = Plugin.find(__name__)
config = plugin.cfg()

REPO_LIST_FILENAME = 'cds_repo_list'

class CdsGoferReceiver(object):

    @identity
    def getuuid(self):
        '''
        Returns the bus ID on which this plugin will receive messages.

        @return: bus name used by gofer
        @rtype:  string
        '''
        return 'cds-%s' % socket.gethostname()

    @remote
    def initialize(self):
        '''
        Performs any initialization needed when a pulp server registered this CDS.

        Currently, this is simply a logging operation to keep record of the fact. It
        is also used as a ping mechanism to make sure the CDS is running before pulp
        acknowledges it was successfully registered.
        '''
        log.info('Received initialize call')

    @remote
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

        num_threads = config.cds.sync_threads
        packages_location = config.cds.packages_dir

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

        packages_dir = config.cds.packages_dir

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

if __name__ == '__main__':
    r = {'name'          : 'main-pulp-testing',
         'relative_path' : 'repos/pulp/pulp/testing/fedora-13/x86_64'}

    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.DEBUG)
    cds = CdsGoferReceiver()
    cds._sync_repos([r])
    