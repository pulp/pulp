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

        # This call simply wraps the actual logic so that any errors that occur are logged
        # on the CDS itself before they are re-raised to the pulp server.
        try:
            self._sync(base_url, repos)
        except Exception, e:
            log.exception('Error performing sync')
            raise e

    def _sync(self, base_url, repos):
        '''
        Does the actual logic of the sync method. This is extracted out for cleanliness in
        catching any errors that may arise and logging them before re-raising them. See the
        sync method for documentation.
        '''

        log.info('Received sync call')
        log.info(repos)

        num_threads = config.cds.sync_threads
        packages_location = config.cds.packages_dir

        # Delete any existing repos that were synchronized but are not in the repo list

        # Synchronize all repos that were specified
        for repo in repos:

            url = '%s/%s' % (base_url, repo['relative_path'])
            log.debug('Synchronizing repo at [%s]' % url)
            repo_path = packages_location + repo['relative_path']

            if not os.path.exists(repo_path):
                os.makedirs(repo_path)

            log.debug('Synchronizing repo [%s] from [%s] to [%s]' % (repo['name'], url, repo_path))

            fetch = YumRepoGrinder('', url, num_threads, sslverify=0)
            fetch.fetchYumRepo(repo_path)


if __name__ == '__main__':
    r = {'name'          : 'main-pulp-testing',
         'relative_path' : 'repos/pulp/pulp/testing/fedora-13/x86_64'}

    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.DEBUG)
    cds = CdsGoferReceiver()
    cds._sync([r])
    