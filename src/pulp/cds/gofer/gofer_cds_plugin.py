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
from gofer.decorators import remote, identity
from grinder.RepoFetch import YumRepoGrinder


log = logging.getLogger(__name__)
log.addHandler(logging.FileHandler('/var/log/pulp-cds/gofer.log'))
log.setLevel(logging.DEBUG)
log.info('CDS gofer plugin initialized')


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
    def sync(self, repos):
        '''
        Synchronizes the given repos to this CDS. This list is the definitive list of what
        should be present on the CDS if this call succeeds. That includes removing any
        repos that were previously synchronized but are no longer in the given list of repos.

        @param repos: list of repos that should be on the CDS following synchronization
        @type  repos: list of dict, where each dict describes a repo that should be present
                      on the CDS
        '''

        # This call simply wraps the actual logic so that any errors that occur are logged
        # on the CDS itself before they are re-raised to the pulp server.
        try:
            self._sync(repos)
        except Exception, e:
            log.exception('Error performing sync')
            raise e

    def _sync(self, repos):

        log.info('Received sync call')
        log.info(repos)

        num_threads = 10
        pulp_server_hostname = '192.168.0.201'
        packages_location = '/pulp-cds/'

        # Delete any existing repos that were synchronized but are not in the repo list

        # Synchronize all repos that were specified
        for repo in repos:

            url = 'https://%s/pulp/repos/%s' % (pulp_server_hostname, repo['relative_path'])
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
    