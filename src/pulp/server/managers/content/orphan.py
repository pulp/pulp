# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


class OrphanManager(object):

    def list_all_orphans(self):
        pass

    def list_orphans_by_type(self, content_type):
        pass

    def delete_all_orphans(self):
        pass

    def delete_orphans_by_type(self, content_type):
        pass

    def delete_orphans_by_id(self, orphan_ids):
        pass

