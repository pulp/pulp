#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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

## Simple file you can run with ipython if you want to poke around the API ##
import sys
sys.path.append("../../src")
sys.path.append("../common")
from pulp.server.api.repo import RepoApi
from pulp.server.api.role import RoleApi
from pulp.server.api.user import UserApi
from pulp.server.util import random_string

from pulp.server.db.model import Permission
from pulp.server.db.model import RoleActionType
from pulp.server.db.model import RoleResourceType


import testutil

repoapi = RepoApi()
roleapi = RoleApi()
userapi = UserApi()

roleapi.clean()
repoapi.clean()

repo = repoapi.create('perm-test-repo', 'perm-test', 'i386')

desc = 'Repository Administrator Role'
action_type = [RoleActionType.CREATE, RoleActionType.WRITE, RoleActionType.READ]
resource_type = RoleResourceType.REPO
role = roleapi.create('repo-admin', desc, action_type, resource_type)


admin = userapi.user('admin')

roleapi.add_instance(repo['id'], role['name'])

roleapi.add_user(role, admin)

