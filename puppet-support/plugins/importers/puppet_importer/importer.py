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

from gettext import gettext as _

import copier
import sync
import upload
import validation
from   pulp_puppet.common import constants

from pulp.plugins.importer import Importer

# -- plugins ------------------------------------------------------------------

class PuppetModuleImporter(Importer):

    @classmethod
    def metadata(cls):
        return {
            'id' : constants.IMPORTER_ID_PUPPET,
            'display_name' : _('Puppet Importer'),
            'types' : [constants.TYPE_PUPPET_MODULE]
        }

    def validate_config(self, repo, config, related_repos):
        return validation.validate(config)

    def sync_repo(self, repo, sync_conduit, config):
        sync_runner = sync.PuppetModuleSyncRun(repo, sync_conduit, config)
        report = sync_runner.perform_sync()
        return report

    def import_units(self, source_repo, dest_repo, import_conduit, config,
                     units=None):
        copier.copy_units(import_conduit, units)

    def upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit,
                    config):
        upload.handle_uploaded_unit(type_id, unit_key, metadata, file_path, conduit)
