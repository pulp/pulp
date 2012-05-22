#
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
#

"""
Pulp (gofer) plugin.
Contains recurring actions and remote classes.
"""

from logging import getLogger

from gofer.decorators import remote

from pulp.client.consumer.goferbase import PulpGoferPlugin, getsecret
from pulp.client.consumer.plugins.consumer import ConsumerClientPlugin

log = getLogger(__name__)

class ConsumerXXX(PulpGoferPlugin):
    """
    Pulp (pulp.repo) yum repository object.
    """

    _pulp_plugin = ConsumerClientPlugin

    def __init__(self):
        PulpGoferPlugin.__init__(self)
        self.consumer = self.pulp_plugin.consumer
    
    @remote(secret=getsecret)
    def bind(self, repo_id, bind_data):
        """
        Binds the repo described in bind_data to this consumer.
        """
        log.info('Binding repo [%s]' % repo_id)
        self.consumer.bind.bind_repo(repo_id, bind_data)

    @remote(secret=getsecret)
    def unbind(self, repo_id):
        """
        Unbinds the given repo from this consumer.
        """
        log.info('Unbinding repo [%s]' % repo_id)
        self.consumer.unbind.unbind_repo(repo_id)

    @remote(secret=getsecret)
    def update(self, repo_id, bind_data):
        '''
        Updates a repo that was previously bound to the consumer. Only the changed
        information will be in bind_data.
        '''
        log.info('Updating repo [%s]' % repo_id)

        repo_file = self.cfg.client.repo_file
        mirror_list_file = repolib.mirror_list_filename(self.cfg.client.mirror_list_dir, repo_id)
        gpg_keys_dir = self.cfg.client.gpg_keys_dir

        repolib.bind(repo_file, mirror_list_file, gpg_keys_dir, repo_id,
                     bind_data['repo'], bind_data['host_urls'], bind_data['gpg_keys'])

    @remote(secret=getsecret)
    def unregistered(self):
        """
        Notification that the consumer has been unregistered.
        Clean up associated artifacts.
        """
        try:
            log.info('Unregistered')
            self.consumer.unregister.delete_files(self.bundle)
        except Exception:
            log.exception('Artifact clean up, failed')
        log.info('Artifacts deleted')
