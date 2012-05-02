
# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import re
from pulp.server.db.model import Repo

_LOG = logging.getLogger('pulp')

version = 41

CONFLICT_MESSAGE = '''
ID for repositories %s contains characters which are not supported by Yum as a repository title in a '.repo' file.
Because of this, you may see an error when installing a package from these repositories on a consumer. You can either 
manually update consumer's .repo file to update title, or delete and create a new repository that follows new ID restriction. 
Repository ID may now contain only numbers(0-9), upper and lower case letters(A-Z, a-z), hyphens(-), underscore(_) and periods(.)
'''

def migrate():
    _LOG.info('migration to data model version %d started' % version)

    repos = list(Repo.get_collection().find())
    invalid_repo_ids = []

    for repo in repos:
        if invalid_id(repo['id']):
            invalid_repo_ids.append(encode_unicode(repo['id']))
            
    if repos:
        msg = CONFLICT_MESSAGE % invalid_repo_ids
        _LOG.warn(msg)
        print(msg)

    _LOG.info('migration to data model version %d complete' % version)

    return True


def invalid_id(id):
    """
    Returns true if id is not compliant with restrictions defined by following regex
    """
    if re.search("[^\w\-.]", id):
        return True
    return False

def encode_unicode(id):
    """
    Check if given id is of type unicode and if yes, return utf-8 encoded id
    """
    if type(id) is unicode:
        id = id.encode('utf-8')
    return id
