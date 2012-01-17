# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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

from pulp.server.api.distribution import DistributionApi
from pulp.server.auth.authorization import CREATE, READ, DELETE
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler, collection_query)
from pulp.server.webservices.http import extend_uri_path

# globals ---------------------------------------------------------------------

api = DistributionApi()
log = logging.getLogger('pulp')

# controllers -----------------------------------------------------------------

class Distributions(JSONController):

    @error_handler
    @auth_required(READ)
    @collection_query("id", "repoids")
    def GET(self, spec={}):
        """
        [[wiki]]
        title: List all available distributions.
        description: Get a list of all distributions managed by Pulp.
        method: GET
        path: /distributions/
        permission: READ
        success response: 200 OK
        failure response: None
        return: list of distribution objects, possibly empty
        example:
        {{{
        #!js
        [{'_id': 'ks-Fedora-Fedora-14-x86_64',
          '_ns': 'distribution',
          'description': None,
          'id': 'ks-Fedora-Fedora-14-x86_64',
          'family' : 'Fedora',
          'variant' : 'Fedora',
          'version' : '14',
          'arch' : 'x86_64',
          'timestamp' : '2011-05-13T15:44:30',
          'files': ['/var/lib/pulp/distributions/ks-Fedora-Fedora-14-x86_64/images/install.img',
                   '/var/lib/pulp/distributions/ks-Fedora-Fedora-14-x86_64/images/efiboot.img',
                   '/var/lib/pulp/distributions/ks-Fedora-Fedora-14-x86_64/images/boot.iso',
                   '/var/lib/pulp/distributions/ks-Fedora-Fedora-14-x86_64/images/efidisk.img',
                   '/var/lib/pulp/distributions/ks-Fedora-Fedora-14-x86_64/images/pxeboot/initrd.img',
                   '/var/lib/pulp/distributions/ks-Fedora-Fedora-14-x86_64/images/pxeboot/vmlinuz'],
          'relativepath' : '/var/lib/pulp/distributions/ks-Fedora-Fedora-14-x86_64'},]
        }}}
        """
        distributions = api.distributions(spec)
        return self.ok(distributions)


class Distribution(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, id):
        """
        [[wiki]]
        title: Look up distribution by id.
        description: Get a distribution object
        method: GET
        path: /distributions/<id>/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found if the id does not match a distribution
        return: a Distribution object
        example:
        {{{
        #!js
        { "id": "ks-Fedora-None-16-x86_64",
          "_id": "ks-Fedora-None-16-x86_64",
          "_ns": "distribution",
          "description": "ks-Fedora-Fedora-16-x86_64",
         "family": "Fedora",
         "relativepath": "/var/lib/pulp/distributions/ks-Fedora-Fedora-16-x86_64",
         "variant": Fedora,
         "version": "16",
         "timestamp": "2011-11-03T07:39:38",
         "arch": "x86_64",
         "url": ["http://localhost/pulp/ks/released/F-16/GOLD/Everything/x86_64/os/"]}
         "files": ["/var/lib/pulp/distributions/ks-Fedora-Fedora-16-x86_64/initrd.img",
           "/var/lib/pulp/distributions/ks-Fedora-Fedora-16-x86_64/repomd.xml",
           "/var/lib/pulp/distributions/ks-Fedora-Fedora-16-x86_64/vmlinuz",
           "/var/lib/pulp/distributions/ks-Fedora-Fedora-16-x86_64/.treeinfo",
           "/var/lib/pulp/distributions/ks-Fedora-Fedora-16-x86_64/efiboot.img",
           "/var/lib/pulp/distributions/ks-Fedora-Fedora-16-x86_64/boot.iso",
           "/var/lib/pulp/distributions/ks-Fedora-Fedora-16-x86_64/efidisk.img"]}
        }}}
        """  
        distro = api.distribution(id)
        if distro is None:
            return self.not_found('No distribution %s' % id)
        # implement filters
        return self.ok(distro)

# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Distributions',
    '/([^/]+)/$', 'Distribution',
)

application = web.application(URLS, globals())
