#!/usr/bin/python
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

'''
This module contains utilities to support the consumer-related operations that are
used outside of consumer API itself.
'''

from pulp.server.config import config
from pulp.server.db.model.resource import Consumer


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
    server_name = config.get('server', 'server_name')
    hostnames.append(server_name)

    repo_hosted_url = config.get('server', 'relative_url')
    repo_relative_path = repo['relative_path']
    repo_urls = []
    for host in hostnames:
        repo_url = 'https://%s%s/%s' % (host, repo_hosted_url, repo_relative_path)
        repo_urls.append(repo_url)

    bind_data = {
        'repo' : repo,
        'host_urls' : repo_urls,
        'gpg_keys' : key_list,
    }

    return bind_data