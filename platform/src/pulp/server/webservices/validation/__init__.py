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
Validation package that contains modules for validating HTTP input for
manipulating resources in the top-level collections.

This package implements a module per top-level collection and the imports that
module directly into the package to avoid namespace collisions. A developer only
needs to import this package to use the validation modules it contains.

For example:

from pulp.server.webservices import validation
input = validation.repo.update_input()
"""

import timeout

__all__ = ['timeout']
