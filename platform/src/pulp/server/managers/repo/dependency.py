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

class DependencyManager(object):

    def resolve_dependencies_by_criteria(self, repo_id, criteria):
        """
        Calculates dependencies for units in the given repositories. The
        repository's importer is used to perform the calculation. The units
        to resolve dependencies for are calculated by applying the given
        criteria against the repository.

        @param repo_id: identifies the repository
        @type  repo_id: str

        @param criteria:
        @type  criteria: UnitAssociationCriteria

        @return: list of units that the given units are dependent upon
        @rtype:  list
        """
        pass

    def resolve_dependencies_by_units(self, repo_id, units):
        """
        Calculates dependencies for the given set of units in the given
        repository.

        @param repo_id:
        @param units:
        @return:
        """
        pass