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
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.user import UserApi

from pulp.server.db.model import Package
from pulp.server.db.model import Consumer
from pulp.server.db.model import Repo
from pulp.server.util import random_string

import testutil

capi = ConsumerApi()
papi = PackageApi()
rapi = RepoApi()
uapi = UserApi()
