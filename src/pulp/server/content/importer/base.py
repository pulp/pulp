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


class Importer(object):

    def __init__(self, **options):
        self.__dict__.update(options)

    @classmethod
    def metadata(cls):
        return {}

    def sync(self, repo_data, importer_config, sync_config, sync_hook):
        raise NotImplementedError()

    def delete_repo(self, repo_data, importer_config, delete_config, delete_hook):
        raise NotImplementedError()
