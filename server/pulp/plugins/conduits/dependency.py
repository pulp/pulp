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

from pulp.plugins.conduits.mixins import ImporterScratchPadMixin, RepoScratchPadMixin, SingleRepoUnitsMixin, ImporterConduitException

class DependencyResolutionConduit(RepoScratchPadMixin, ImporterScratchPadMixin, SingleRepoUnitsMixin):

    def __init__(self, repo_id, importer_id):
        RepoScratchPadMixin.__init__(self, repo_id, ImporterConduitException)
        ImporterScratchPadMixin.__init__(self, repo_id, importer_id)
        SingleRepoUnitsMixin.__init__(self, repo_id, ImporterConduitException)
