# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

from pulp.server.db import version


class Migration(object):

    def __init__(self, version_number):
        self.version_number = version_number

    # document utility methods

    def add_field_with_default(self, objectdb, field, default=None):
        pass

    # migration methods

    def migrate(self):
        pass

    def set_version(self):
        version.set_version_in_db(self.version_number)
