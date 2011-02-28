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
Round-robin algorithm for distributing consumers across CDS-repo pairings.

Given CDS instances A, B, and C, all serving repo X, the following describes
the order in which the CDS URL list will be returned for subsequent consumer
bind calls:
1.  A, B, C
2.  B, C, A
3.  C, A, B
4.  A, B, C

When a new CDS-repo pairing is added, the newly added CDS will be added to
the front of the next permutation returned. At that point, it will become
subject to the same rotation as other CDS instances. In other words, the
generation call will not take steps to bring the newly added CDS up to
the same load as the previous instances. In such a case, the
redistribute call can be used to retrieve a list of permutations that evenly
distribute across all CDS instances for the given repo. These permutations can
then be sent to consumers to rebalance the system.
'''

from pulp.server.db.model.cds import CDSRepoRoundRobin


# -- public api ---------------------------------------------------------------------------

def generate_cds_urls(repo):
    '''
    Generates an ordered list of URLs that should be used to access the given repo.

    @param repo: the repo to which to generate the list of URLs
    @type  repo: L{Repo}

    @return: list of URLs used to access the given rep
    @rtype:  list of strings; empty list if there are no CDS instances associated with the
             repo
    '''
    objectdb = CDSRepoRoundRobin.get_collection()

    if objectdb.find({'repo_id' : repo['id']}) is None:
        return []



def redistribute(repo):
    '''
    Decide between pre-generating list and returning an iterator.
    '''
    

def add_cds_repo_association(cds_hostname, repo_id):
    '''
    Adds a CDS for consideration in generating the CDS URL list for the given
    repo. This method does not check to ensure a repo with the given ID exists;
    that must be checked prior to calling this method. If the association already
    exists, no change is made.

    @param cds_hostname: identifies the CDS
    @type  cds_hostname: string

    @param repo_id: identifies the repo
    @type  repo_id: string

    @return: True if a new association was created; False if one already existed between
             the CDS and repo
    @rtype:  boolean
    '''

    objectdb = CDSRepoRoundRobin.get_collection()

    # If there is no association collection for the repo, add one now
    association = _find_association(repo_id)
    if association is None:
        association = CDSRepoRoundRobin(repo_id, [])

    # Punch out if the association already exists
    if cds_hostname in association['next_permutation']:
        return False
        
    # The new CDS should be the first returned at the next assignment
    association['next_permutation'] = [cds_hostname] + association['next_permutation']
    
    objectdb.save(association)

    return True

def remove_cds_repo_association(cds_hostname, repo_id):
    '''
    Removes a CDS from consideration in the CDS URL list generation for the given
    repo. If no association between the repo and CDS exists, this method has no
    effect.

    @param cds_hostname: identifies the CDS
    @type  cds_hostname: string

    @param repo_id: identifies the repo
    @type  repo_id: string

    @return: True if a new association was removed; False if the association did not exist
    @rtype:  boolean
    '''

    objectdb = CDSRepoRoundRobin.get_collection()

    # If there is no association for the repo, punch out early
    association = _find_association(repo_id)
    if association is None:
        return False

    # The new CDS should be the first returned at the next assignment
    if cds_hostname in association['next_permutation']:
        association['next_permutation'].remove(cds_hostname)
        objectdb.save(association)
        return True
    else:
        return False


# -- private api --------------------------------------------------------------------------

def _find_association(repo_id):
    objectdb = CDSRepoRoundRobin.get_collection()
    found_association = list(objectdb.find(spec={'repo_id' : repo_id}))
    if not found_association:
        return None
    else:
        return found_association[0]
