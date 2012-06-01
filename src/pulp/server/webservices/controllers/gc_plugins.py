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

# Python
import logging

# 3rd Party
import web

# Pulp
from pulp.server.auth.authorization import READ
import pulp.server.managers.factory as manager_factory
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------

class Types(JSONController):

    # GET: Return all type definitions

    @auth_required(READ)
    def GET(self):
        manager = manager_factory.plugin_manager()
        type_defs = manager.types()
        return self.ok(type_defs)

class Importers(JSONController):

    # GET: Return all importers present in the server

    @auth_required(READ)
    def GET(self):
        manager = manager_factory.plugin_manager()
        importers = manager.importers()
        return self.ok(importers)

class Distributors(JSONController):

    # GET: Return all distributors present in the server

    @auth_required(READ)
    def GET(self):
        manager = manager_factory.plugin_manager()
        distributors = manager.distributors()
        return self.ok(distributors)

# -- web.py application -------------------------------------------------------

urls = (
    '/types/$', 'Types',
    '/importers/$', 'Importers',
    '/distributors/$', 'Distributors',
)

application = web.application(urls, globals())
