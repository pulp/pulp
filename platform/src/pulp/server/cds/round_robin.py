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


# -- support classes ----------------------------------------------------------------------

class Iterator(object):
    '''
    Calculates the next permutation in the CDS list based on the algorithm defined in
    the module-level docs. An instance of this object is returned on a redistribute
    call to allow a large number of permutations to be generated without incurring
    the database access penalty between generations.

    It is critical to realize the save() method must be called when the permutations
    are finished being generated to save the state of the last generation to the database.
    '''

    def __init__(self, repo_id, seed):
        self.repo_id = repo_id
        self.next_permutation = seed

    def next(self):
        '''
        Returns the next permutation.

        @return: next list of CDS hostnames according to the generation algorithm
        @rtype:  list of strings
        '''
        perm = self.next_permutation
        self.next_permutation = Iterator._next(perm)
        return perm

    def save(self):
        '''
        Saves the state of the permutations based on the current state of the iterator.
        This call accesses the database and is best used once all permutations have been
        generated.
        '''
        association = _find_association(self.repo_id)
        association['next_permutation'] = self.next_permutation
        CDSRepoRoundRobin.get_collection().save(association, safe=True)

    @classmethod
    def _next(cls, seed):
        '''
        Calculates the next permutation based on the provided seed according to the
        algorithm defined in the module-level documentation.
        '''
        return seed[1:] + seed[:1]

# -- public api ---------------------------------------------------------------------------

def generate_cds_urls(repo_id):
    '''
    Generates an ordered list of CDS hostnames that should be used to access the given repo.

    @param repo_id: identifies the repo to which to generate the list of hostnames
    @type  repo_id: string

    @return: list of hostnames used to access the given rep
    @rtype:  list of strings; empty list if there are no CDS instances associated with the
             repo
    '''

    # If there is no association of CDSes to the repo, return an empty list
    association = _find_association(repo_id)
    if association is None:
        return []

    # Hold on to a copy of this to return to the caller
    perm = list(association['next_permutation'])

    # Generate the next permutation and save it
    association['next_permutation'] = Iterator._next(list(perm))
    CDSRepoRoundRobin.get_collection().save(association, safe=True)

    # Return the permutation to the caller
    return perm


def iterator(repo_id):
    '''
    Returns an iterator capable of generating permutations for the repo with the given ID.
    If there are no CDSes assigned to the given repo, None will be returned.

    Once finished generating permutations with this iterator, its save() method must be called
    to save the state of the last generated permutation. Keep in mind the save() call writes
    to the database, so be careful to avoid calling it in large loops.

    @param repo_id: identifies the repo to which CDS hostname permutations will be generated;
                    at least one CDS should be associated with this repo prior to calling this
    @type  repo_id: string

    @return: iterator used to produce CDS hostname permutations for the given repo
    @rtype:  L{Iterator}
    '''

    # Sanity check that the iterator makes sense to return
    association = _find_association(repo_id)
    if association is None:
        return None

    return Iterator(repo_id, association['next_permutation'])

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
    
    objectdb.save(association, safe=True)

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

        # If there are no more CDS instances in the association document,
        # remove the document entirely
        if len(association['next_permutation']) is 0:
            objectdb.remove({'repo_id' : repo_id}, safe=True)
        else:
            objectdb.save(association, safe=True)
        
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
