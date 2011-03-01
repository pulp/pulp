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

from pulp.server.db.model.resource import Consumer

def consumers_bound_to_repo(repo_id):
    '''
    Returns a list of consumers that are bound to the given repo.

    @param repo_id: ID(s) of the repo(s) to search for bindings; this may be a single
                    ID (string) or a list of multiple IDs (list or tuple)
    @type  repo_id: string, list, or tuple

    @return: list of consumer objects; empty list if none are bound
    @rtype:  list of L{Consumer}
    '''
    if type(repo_id) is not list and type(repo_id) is not tuple:
        repo_id = [repo_id]

    return list(Consumer.get_collection().find({'repoids' : repo_id}))
