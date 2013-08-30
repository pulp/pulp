# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import httplib

from pulp_node import resources
from pulp_node.error import ImporterNotInstalled, DistributorNotInstalled


# --- constants --------------------------------------------------------------


TYPE_ID = 'id'
REPO_ID = 'id'
DISTRIBUTOR_TYPE_ID = 'distributor_type_id'
IMPORTER_TYPE_ID = 'importer_type_id'
IMPORTERS = 'importers'
DISTRIBUTORS = 'distributors'
REPOSITORY = 'repository'
DETAILS = 'details'

# --- validation -------------------------------------------------------------


class Validator(object):
    """
    Validate that a child server is in the proper state to be synchronized.
    """

    def __init__(self, report):
        """
        :param report: A strategy reported used for error reporting.
        :type report: pulp_node.handlers.reports.StrategyReport
        :return:
        """
        self.report = report

    def validate(self, bindings):
        """
        Validate that the child node is suitable for synchronization.
        :param bindings: A list of binding payloads.
        :type bindings: list
        :return:
        """
        self.report.errors.extend(self._validate_db_versions())
        self.report.errors.extend(self._validate_plugins(bindings))

    def _validate_db_versions(self):
        """
        Validate that the database versions are compatible.
        """
        # Future
        return []

    def _validate_plugins(self, bindings):
        """
        Validate that all plugins referenced in the bindings are installed.
        :param bindings: A list of binding payloads.
        :type bindings: list
        """
        errors = []
        child = ChildServer()
        for binding in bindings:
            details = binding[DETAILS]
            repo_id = details[REPOSITORY][REPO_ID]
            for plugin in details[IMPORTERS]:
                type_id = plugin[IMPORTER_TYPE_ID]
                if not child.has_importer(type_id):
                    errors.append(ImporterNotInstalled(repo_id, type_id))
            for plugin in details[DISTRIBUTORS]:
                type_id = plugin[DISTRIBUTOR_TYPE_ID]
                if not child.has_distributor(type_id):
                    errors.append(DistributorNotInstalled(repo_id, type_id))
        return errors


class ChildServer(object):

    def __init__(self):
        self.importers = self._importers()
        self.distributors = self._distributors()

    def has_importer(self, type_id):
        return type_id in self.importers

    def has_distributor(self, type_id):
        return type_id in self.distributors

    def _importers(self):
        bindings = resources.pulp_bindings()
        http = bindings.server_info.get_importers()
        if http.response_code == httplib.OK:
            return set([p[TYPE_ID] for p in http.response_body])
        else:
            raise Exception('get importers failed:%d', http.response_code)

    def _distributors(self):
        bindings = resources.pulp_bindings()
        http = bindings.server_info.get_distributors()
        if http.response_code == httplib.OK:
            return set([p[TYPE_ID] for p in http.response_body])
        else:
            raise Exception('get distributors failed:%d', http.response_code)