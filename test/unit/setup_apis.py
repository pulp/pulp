#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

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
