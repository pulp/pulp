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
from pulp.server.exceptions import MissingResource
import pulp.server.managers.factory as manager_factory
from pulp.server.webservices.serialization import link
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

        for t in type_defs:
            href = link.child_link_obj(t['id'])
            t.update(href)

        return self.ok(type_defs)

class Type(JSONController):

    # GET: Return a single type definition

    @auth_required(READ)
    def GET(self, type_id):
        manager = manager_factory.plugin_manager()
        all_types = manager.types()

        matching_types = [t for t in all_types if t['id'] == type_id]

        if len(matching_types) is 0:
            raise MissingResource(type=type_id)
        else:
            t = matching_types[0]
            href = link.current_link_obj()
            t.update(href)

            return self.ok(t)

class Importers(JSONController):

    # GET: Return all importers present in the server

    @auth_required(READ)
    def GET(self):
        manager = manager_factory.plugin_manager()
        importers = manager.importers()

        for i in importers:
            href = link.child_link_obj(i['id'])
            i.update(href)

        return self.ok(importers)

class Importer(JSONController):

    # GET: Return details on a single importer

    @auth_required(READ)
    def GET(self, importer_type_id):
        manager = manager_factory.plugin_manager()
        all_importers = manager.importers()

        matching_importers = [i for i in all_importers if i['id'] == importer_type_id]

        if len(matching_importers) is 0:
            raise MissingResource(importer_type_id=importer_type_id)
        else:
            i = matching_importers[0]
            href = link.current_link_obj()
            i.update(href)

            return self.ok(i)

class Distributors(JSONController):

    # GET: Return all distributors present in the server

    @auth_required(READ)
    def GET(self):
        manager = manager_factory.plugin_manager()
        distributors = manager.distributors()

        for d in distributors:
            href = link.child_link_obj(d['id'])
            d.update(href)

        return self.ok(distributors)

class Distributor(JSONController):

    # GET: Return details on a single distributor

    @auth_required(READ)
    def GET(self, distributor_type_id):
        manager = manager_factory.plugin_manager()
        all_distributors = manager.distributors()

        matching_distributors = [d for d in all_distributors if d['id'] == distributor_type_id]

        if len(matching_distributors) is 0:
            raise MissingResource(distributor_type_id=distributor_type_id)
        else:
            d = all_distributors[0]
            href = link.current_link_obj()
            d.update(href)

            return self.ok(d)

# -- web.py application -------------------------------------------------------

urls = (
    '/types/$', 'Types',
    '/types/([^/]+)/$', 'Type',

    '/importers/$', 'Importers',
    '/importers/([^/]+)/$', 'Importer',

    '/distributors/$', 'Distributors',
    '/distributors/([^/]+)/$', 'Distributor',
)

application = web.application(urls, globals())
