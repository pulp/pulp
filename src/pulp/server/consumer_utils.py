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

'''
This module contains utilities to support the consumer-related operations that are
used outside of consumer API itself.
'''

import pulp.server.config
from pulp.server.db.model.resource import Consumer
from logging import getLogger


# Temporary hack to use V2 repositories with V1 consumers. This will be removed once consumers are migrated to V2.
import pulp.server.managers.factory as manager_factory

log = getLogger(__name__)


def consumers_bound_to_repo(repo_id):
    '''
    Returns a list of consumers that are bound to the given repo.

    @param repo_id: ID of the repo to search for bindings
    @type  repo_id: string

    @return: list of consumer objects; empty list if none are bound
    @rtype:  list of L{Consumer}
    '''
    return list(Consumer.get_collection().find({'repoids' : repo_id}))

def build_bind_data(repo, hostnames, key_list):
    '''
    Builds the data bundle that will be sent to consumers for a bind request.
    The Pulp server itself will automatically be added to the list of provided
    hostnames at the end.

    Any data the caller needs to use the newly bound repo is returned. The data is
    returned in a dictionary. The keys in the dictionary and what they represent
    are as follows:
    - repo: the repo object itself
    - host_urls: an ordered list of full URLs to use to access the repo
    - gpg_keys: a list of full URLs to all gpg keys (if any) associated with the repo;
                empty list if the repo does not define any GPG keys

    @param repo: repo object describing the repo being bound
    @type  repo: L{Repo}

    @param hostnames: list of CDS hostnames the consumer will be bound to
    @type  hostnames: list of strings; may be an empty list

    @param key_list: list of keys associated with the repo
    @type  key_list: list of strings

    @return: dictionary of data to send to a consumer for a bind
    @rtype:  dict
    '''

    if hostnames is None:
        hostnames = []

    if key_list is None:
        key_list = {}

    # Add in the pulp server itself as the last host in the list if there are CDS
    # instances; if there are none, the pulp server will be the only entry (default case)
    server_name = pulp.server.config.config.get('server', 'server_name')
    hostnames.append(server_name)

    repo_hosted_url = pulp.server.config.config.get('server', 'relative_url')

# <V2 Repo changes>

    #repo_relative_path = repo['relative_path']
    repo_distributor_manager = manager_factory.repo_distributor_manager()
    distributor = repo_distributor_manager.get_distributors(repo['id'])[0]
    repo_relative_path = distributor['config'].get('relative_url')
    
# </V2 Repo changes>

    repo_urls = []
    for host in hostnames:
        repo_url = 'https://%s%s/%s' % (host, repo_hosted_url, repo_relative_path)
        repo_urls.append(repo_url)
        
    # add certificates
    ssl_ca_cert = None
    client_cert = None
    
# <V2 Repo changes>
    #consumer_cert_path = repo.get('consumer_cert')
    consumer_cert_path = distributor['config'].get('auth_cert')
# </V2 Repo changes>

    if consumer_cert_path:
        f = open(consumer_cert_path)
        client_cert = f.read()
        f.close()

        # Only set the ssl ca cert if the repo has been configured to use a
        # consumer cert.
        ssl_ca_cert_path = pulp.server.config.config.get('security', 'ssl_ca_certificate')
        if ssl_ca_cert_path:
            f = open(ssl_ca_cert_path)
            ssl_ca_cert = f.read()
            f.close()

    bind_data = {
# <V2 Repo changes>
        'repo' : repo,
        #'repo' : prune(repo),
# </V2 Repo changes>
        'host_urls' : repo_urls,
        'gpg_keys' : key_list,
        'cacert' : ssl_ca_cert,
        'clientcert' : client_cert,
    }

    return bind_data


def prune(repo):
    '''
    Remove superfluous attributes.
    @param repo: A repo model object.
    @type repo: Repo
    @return: The pruned object
    @rtype: Repo 
    '''
    prune = (
        'packages',
        'package_count',
        'packagegroups',
        'packagegroupcategories',
        'distributionid',
        'sync_schedule',
        'last_sync',
        'sync_in_progress',
        'source',
        'clone_ids',
        'groupid',
        'errata',
        'files',
        'filters',
        'notes',)
    for attr in prune:
        try:
            del repo[attr]
        except ValueError:
            log.error(attr, exc_info=1)
    return repo
