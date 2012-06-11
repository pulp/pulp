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

"""
Queries package containing modules that implement functions that utilize HTTP
query parameters in order to serarch on MongoDB collections.

This package exits to allow REST controllers to use GET query parameters in
order to filter collection and resource results. It implements a submodule per
top-level collection and then imports that module into this package to avoid
namespace collisions. A developer only need to import this package to utilize
the modules within it.

For example:

from pulp.server.webservices import queries
repos = queries.repos.collection()
"""

import repo

__all__ = ['repo']
