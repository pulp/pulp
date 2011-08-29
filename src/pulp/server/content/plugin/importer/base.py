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

from pulp.server.content.plugin.base import ContentPlugin

class Importer(ContentPlugin):

    def __init__(self, config):
        super(Importer, self).__init__(config)

    def sync(self, repo_data, importer_config, sync_config, sync_conduit):
        raise NotImplementedError()

    def pre_import_unit(self, repo_data, importer_config, unit_data):
        pass

    def import_unit(self, importer_config, unit_data, unit_temp_dir):
        raise NotImplementedError()

    def delete_repo(self, repo_data, importer_config, delete_config, delete_conduit):
        raise NotImplementedError()
