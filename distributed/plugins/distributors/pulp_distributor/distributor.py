# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.plugins.distributor import Distributor

class PulpDistributor(Distributor):

    @classmethod
    def metadata(cls):
        return {
            'id':'pulp_distributor',
            'display_name':'Pulp Distributor',
            'types':['repository',]
        }

    def validate_config(self, repo, config, related_repos):
        return (True, None)

    def publish_repo(self, repo, publish_conduit, config):
        pass
    
    def cancel_publish_repo(self, call_report, call_request):
        pass
    
    def create_consumer_payload(self, repo, config):
        payload = {'mypayload':'MYPAYLOAD'}
        return payload