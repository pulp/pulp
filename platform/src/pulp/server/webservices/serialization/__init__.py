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
Serialization package to transform Pulp's persistent resources from the database
representation to a representation compatible with REST.

This package supplies sub-modules, one per database collection. Each module
supplies a number of methods to transform output for consumption by a REST
client. The sub-modules are imported directly into this package to avoid
namespace collisions. A developer only needs to import this package to use all
the serialization modules.

For example:

from pulp.server.webservices import serialization
repo_repr = serialization.repo.serialize(repo)
"""

import binding
import content
import dispatch
import error
import link
import consumer

__all__ = ['binding', 'content', 'dispatch', 'error', 'link', 'consumer']
