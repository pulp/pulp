# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server.db.model.consumer import Bind


BINDING_CONFIG = 'binding_config'
QUERY = {BINDING_CONFIG: None}
UPDATE = {'$set': {BINDING_CONFIG: {}}}


def migrate(*args, **kwargs):
    """
    Set binding_config = {} on all bindings with binding_config of None.
    Earlier versions of pulp permitted the binding to be created with
    a binding_config of None.
    """
    collection = Bind.get_collection()
    collection.update(QUERY, UPDATE, multi=True, safe=True)
