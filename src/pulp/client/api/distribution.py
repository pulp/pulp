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

from pulp.client.api.base import PulpAPI


class DistributionAPI(PulpAPI):
    """
    Connection class to access distribution related calls
    """
    def clean(self):
        pass

    def distributions(self):
        path = '/distributions/'
        return self.server.GET(path)[1]

    def distribution(self, id):
        path = '/distributions/%s/' % str(id)
        return self.server.GET(path)[1]

