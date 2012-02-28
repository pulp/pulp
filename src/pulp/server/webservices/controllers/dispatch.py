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

import web

from pulp.server.auth import authorization
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

# globals ----------------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# task controllers -------------------------------------------------------------

class TaskCollection(JSONController):

    @auth_required(authorization.READ)
    def GET(self):
        pass


class TaskResource(JSONController):

    @auth_required(authorization.READ)
    def GET(self, task_id):
        pass

    @auth_required(authorization.DELETE)
    def DELETE(self, task_id):
        pass

# job controllers --------------------------------------------------------------

class JobCollection(JSONController):

    @auth_required(authorization.READ)
    def GET(self):
        pass


class JobResource(JSONController):

    @auth_required(authorization.READ)
    def GET(self, job_id):
        pass

    @auth_required(authorization.DELETE)
    def DELETE(self, job_id):
        pass

# web.py applications ----------------------------------------------------------

TASK_URLS = (
    '/', TaskCollection,
    '/([^/]+)/', TaskResource,
)

task_application = web.application(TASK_URLS, globals())


JOB_URLS = (
    '/', JobCollection,
    '/([^/]+)/', JobResource,
)

job_application = web.application(JOB_URLS, globals())

