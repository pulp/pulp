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

from gettext import gettext as _


class NodeError(Exception):

    def __init__(self, error_id, **details):
        self.error_id = error_id
        self.details = details

    def load(self, _dict):
        if isinstance(_dict, dict):
            self.__dict__.update(_dict)
        else:
            raise ValueError(_dict)

    def dict(self):
        return self.__dict__

    def __eq__(self, other):
        return self.error_id == other.error_id and self.details == other.details


class CaughtException(NodeError):

    ERROR_ID = 'exception'
    DESCRIPTION = _('An unexpected error occurred.  repo_id=%(repo_id)s')

    def __init__(self, exception, repo_id=None):
        super(CaughtException, self).__init__(
            self.ERROR_ID, message=str(exception), repo_id=repo_id)

    def __str__(self):
        return self.DESCRIPTION % self.details


class PurgeOrphansError(NodeError):

    ERROR_ID = 'rest.child.orphans.purge'
    DESCRIPTION = _('Purge orphans failed with http code [%(http_code)s].')

    def __init__(self, http_code):
        super(PurgeOrphansError, self).__init__(self.ERROR_ID, http_code=http_code)

    def __str__(self):
        return self.DESCRIPTION % self.details


class RepoSyncRestError(NodeError):

    ERROR_ID = 'rest.child.repository.synchronization'
    DESCRIPTION = _('Repository synchronization failed with http code [%(http_code)s].')

    def __init__(self, repo_id, http_code):
        super(RepoSyncRestError, self).__init__(self.ERROR_ID, repo_id=repo_id, http_code=http_code)

    def __str__(self):
        return self.DESCRIPTION % self.details


class GetBindingsError(NodeError):

    ERROR_ID = 'rest.parent.bindings.get'
    DESCRIPTION = _('Get bindings from the parent failed with http code [%(http_code)s].')

    def __init__(self, http_code):
        super(GetBindingsError, self).__init__(self.ERROR_ID, http_code=http_code)

    def __str__(self):
        return self.DESCRIPTION % self.details


class GetChildUnitsError(NodeError):

    ERROR_ID = 'rest.child.units.get'
    DESCRIPTION = _('Get units in repository [%(repo_id)s] from the child failed.')

    def __init__(self, repo_id):
        super(GetChildUnitsError, self).__init__(self.ERROR_ID, repo_id=repo_id)

    def __str__(self):
        return self.DESCRIPTION % self.details


class GetParentUnitsError(NodeError):

    ERROR_ID = 'rest.parent.units.get'
    DESCRIPTION = _('An error occurred while downloading units from the parent for '
                    'repository [%(repo_id)s. The cause may be that the repository has not '
                    'been published')

    def __init__(self, repo_id):
        super(GetParentUnitsError, self).__init__(self.ERROR_ID, repo_id=repo_id)

    def __str__(self):
        return self.DESCRIPTION % self.details


class ImporterNotInstalled(NodeError):

    ERROR_ID = 'plugins.child.importer.missing'
    DESCRIPTION = _('The [%(type_id)s] importer is associated with a repository [%(repo_id)s] '
                    'on the parent but is not installed on the child. The plugin providing this '
                    'importer needs to be installed and loaded by restarting httpd.')

    def __init__(self, repo_id, type_id):
        super(ImporterNotInstalled, self).__init__(self.ERROR_ID, repo_id=repo_id, type_id=type_id)

    def __str__(self):
        return self.DESCRIPTION % self.details


class DistributorNotInstalled(NodeError):

    ERROR_ID = 'plugins.child.distributor.missing'
    DESCRIPTION = _('The [%(type_id)s] distributor is associated with a repository [%(repo_id)s] '
                    'on the parent but is not installed on the child. The plugin providing this '
                    'distributor needs to be installed and loaded by restarting httpd.')

    def __init__(self, repo_id, type_id):
        super(DistributorNotInstalled, self).__init__(self.ERROR_ID, repo_id=repo_id, type_id=type_id)

    def __str__(self):
        return self.DESCRIPTION % self.details


class ManifestDownloadError(NodeError):

    ERROR_ID = 'download.parent.manifest'
    DESCRIPTION = _('Received error [%(message)s] while downloading the manifest at '
                    'URL [%(url)s]. The cause could be that the repository has not been published.')

    def __init__(self, url, message):
        super(ManifestDownloadError, self).__init__(self.ERROR_ID, url=url, message=message)

    def __str__(self):
        return self.DESCRIPTION % self.details


class InvalidManifestError(NodeError):

    ERROR_ID = 'manifest.not-valid'
    DESCRIPTION = _('Published manifest not valid . '
                    'The cause is most likely a pulp-nodes software version mismatch between the '
                    'parent and child nodes.  Or, the software has been updated and the repository'
                    '(manifest) needs to be republished.')

    def __init__(self):
        super(InvalidManifestError, self).__init__(self.ERROR_ID)

    def __str__(self):
        return self.DESCRIPTION


class UnitDownloadError(NodeError):

    ERROR_ID = 'download.unit'
    DESCRIPTION = _('Received error [%(message)s] while downloading a unit file at '
                    'URL [%(url)s] for repository [%(repo_id)s]. The cause could be that the '
                    'repository has not been published.')

    def __init__(self, url, repo_id, message):
        super(UnitDownloadError, self).__init__(
            self.ERROR_ID, url=url, repo_id=repo_id, message=message)


class AddUnitError(NodeError):

    ERROR_ID = 'child.unit.add'
    DESCRIPTION = _('Adding a unit associated with repository [%(repo_id)s] failed.')

    def __init__(self, repo_id):
        super(AddUnitError, self).__init__(self.ERROR_ID, repo_id=repo_id)

    def __str__(self):
        return self.DESCRIPTION % self.details


class DeleteUnitError(NodeError):

    ERROR_ID = 'child.unit.delete'
    DESCRIPTION = _('Deleting a unit associated with repository [%(repo_id)s] failed.')

    def __init__(self, repo_id):
        super(DeleteUnitError, self).__init__(self.ERROR_ID, repo_id=repo_id)

    def __str__(self):
        return self.DESCRIPTION % self.details


class ErrorList(list):

    def append(self, error):
        """
        Append the error.
          - Duplicates ignored.
          - Increment the 'count' on Summary Errors.
        :param error: An error to append.
        :type error: NodeError
        """
        if not isinstance(error, NodeError):
            raise ValueError(error)
        if error not in self:
            super(ErrorList, self).append(error)

    def extend(self, iterable):
        """
        Extend the list using append().
        :param iterable: An iterable containing errors.
        :type iterable: iterable
        """
        for e in iterable:
            self.append(e)

    def update(self, **details):
        """
        Update the details of all contained errors.
        :param details: A details dictionary.
        :type details: dict
        """
        for e in self:
            e.details.update(details)
