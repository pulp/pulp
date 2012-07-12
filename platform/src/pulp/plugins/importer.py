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
    """
    Base class for Pulp content importers for a single repository. Importers
    must subclass this class in order for Pulp to identify it as a valid
    importer during discovery.
    """

    # -- plugin lifecycle -----------------------------------------------------

    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this importer. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this importer. Must be unique
               across all importers. Only letters and underscores are valid.
        * display_name - User-friendly identification of the importer.
        * types - List of all content type IDs that may be imported using this
               importer.

        This method call may be made multiple times during the course of a
        running Pulp server and thus should not be used for initialization
        purposes.

        @return: description of the importer's capabilities
        @rtype:  dict
        """
        raise NotImplementedError()

    # -- repo lifecycle -------------------------------------------------------

    def validate_config(self, repo, config, related_repos):
        """
        Allows the importer to check the contents of a potential configuration
        for the given repository. This call is made both for the addition of
        this importer to a new repository as well as updating the configuration
        for this importer on a previously configured repository. The implementation
        should use the given repository data to ensure that updating the
        configuration does not put the repository into an inconsistent state.

        The return is a tuple of the result of the validation (True for success,
        False for failure) and a message. The message may be None and is unused
        in the success case. For a failed validation, the message will be
        communicated to the caller so the plugin should take i18n into
        consideration when generating the message.

        The related_repos parameter contains a list of other repositories that
        have a configured importer of this type. The importer configurations
        is found in each repository in the "plugin_configs" field.

        @param repo: metadata describing the repository to which the
                     configuration applies
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param config: plugin configuration instance; the proposed repo
                       configuration is found within
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @param related_repos: list of other repositories using this distributor
               type; empty list if there are none; entries are of type
               L{pulp.server.content.plugins.data.RelatedRepository}
        @type  related_repos: list

        @return: tuple of (bool, str) to describe the result
        @rtype:  tuple
        """
        raise NotImplementedError()

    def importer_added(self, repo, config):
        """
        Called upon the successful addition of an importer of this type to
        a repository. This hook allows the importer to do any initial setup
        it needs to prior to the first sync.

        This call should raise an exception in the case where the importer
        is unable to successfully set up anything it will need to perform any
        repository actions against the given repository. In this case, Pulp
        will mark the importer as broken and repository operations that rely
        on the importer will be unavailable for the given repository.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.model.Repository}

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}
        """
        pass

    def importer_removed(self, repo, config):
        """
        Called when an importer of this type is removed from a repository.
        This hook allows the importer to clean up any temporary files that may
        have been created during the repository creation or sync process.

        This call does not need to delete any content that has been
        synchronized by this importer. Imported content units are deleted through
        a separate process in Pulp.

        The importer may use the contents of the working directory in cleanup.
        It is not required that the contents of this directory be deleted by
        the importer; Pulp will ensure it is wiped following this call.

        If this call raises an exception, the importer will still be removed
        from the repository and the working directory contents will still
        be wiped by Pulp.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.model.Repository}

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}
        """
        pass

    # -- actions --------------------------------------------------------------

    def upload_unit(self, repo, type_id, unit_key, metadata, file_path, conduit, config):
        """
        Handles a user request to upload a unit into a repository. This call
        should use the data provided to add the unit as if it were synchronized
        from an external source. This includes:

        * Initializing the unit through the conduit which populates the final
          destination of the unit.
        * Deriving any
        * Copy the unit from the provided temporary location into the unit's
          actual path.
        * Save the unit in Pulp, which both adds the unit to Pulp's database and
          associates it to the repository.

        This call may be invoked for either units that do not already exist as
        well as re-uploading an existing unit.

        The metadata parameter is variable in its usage. In some cases, the
        unit may be almost exclusively metadata driven in which case the contents
        of this parameter will be used directly as the unit's metadata. In others,
        it may function to remove the importer's need to derive the unit's metadata
        from the uploaded unit file. In still others, it may be extraneous
        user-specified information that should be merged in with any derived
        unit metadata.

        Depending on the unit type, it is possible that this call will create
        multiple units within Pulp. It is also possible that this call will
        create one or more relationships between existing units.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param type_id: type of unit being uploaded
        @type  type_id: str

        @param unit_key: identifier for the unit, specified by the user
        @type  unit_key: dict

        @param metadata: any user-specified metadata for the unit
        @type  metadata: dict

        @param file_path: path on the Pulp server's filesystem to the temporary
               location of the uploaded file; may be None in the event that a
               unit is comprised entirely of metadata and has no bits associated
        @type  file_path: str

        @param conduit: provides access to relevant Pulp functionality
        @type  conduit: L{pulp.server.content.conduits.unit_add.UnitAddConduit}

        @param config: plugin configuration for the repository
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @return: report of the details of the sync
        @rtype:  L{pulp.server.content.plugins.model.SyncReport}
        """
        raise NotImplementedError()

    def import_units(self, source_repo, dest_repo, import_conduit, config, units=None):
        """
        Import content units into the given repository. This method will be
        called in a number of different situations:
         * A user is attempting to copy a content unit from one repository
           into the repository that uses this importer
         * A user is attempting to add an orphaned unit into a repository.

        This call should perform any changes to the destination repository's
        working directory as necessary.

        The units argument is optional. If None, all units in the source
        repository should be imported. The conduit is used to query for those
        units. If specified, only the units indicated should be imported (this
        is the case where the caller passed a filter to Pulp).

        @param source_repo: metadata describing the repository containing the
               units to import
        @type  source_repo: L{pulp.server.content.plugins.data.Repository}

        @param dest_repo: metadata describing the repository to import units
               into
        @type  dest_repo: L{pulp.server.content.plugins.data.Repository}

        @param import_conduit: provides access to relevant Pulp functionality
        @type  import_conduit: L{pulp.server.content.conduits.unit_import.ImportUnitConduit}

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @param units: optional list of pre-filtered units to import
        @type  units: list of L{pulp.server.content.plugins.data.Unit}
        """
        raise NotImplementedError()

    def remove_units(self, repo, units, remove_conduit):
        """
        Removes content units from the given repository.

        This method is intended to provide the importer with a chance to remove
        the units from the importer's working directory for the repository.

        This call will not result in the unit being deleted from Pulp itself.
        The importer should, however, use the conduit to tell Pulp to remove
        the association between the unit and the given repository.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param units: list of objects describing the units to import in
                      this call
        @type  units: list of L{pulp.server.content.plugins.data.Unit}

        @param remove_conduit: provides access to relevant Pulp functionality
        @type  remove_conduit: ?
        """
        raise NotImplementedError()

    def sync_repo(self, repo, sync_conduit, config):
        """
        Synchronizes content into the given repository. This call is responsible
        for adding new content units to Pulp as well as associating them to the
        given repository.

        While this call may be implemented using multiple threads, its execution
        from the Pulp server's standpoint should be synchronous. This call should
        not return until the sync is complete.

        It is not expected that this call be atomic. Should an error occur, it
        is not the responsibility of the importer to rollback any unit additions
        or associations that have been made.

        The returned report object is used to communicate the results of the
        sync back to the user. Care should be taken to i18n the free text "log"
        attribute in the report if applicable.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param sync_conduit: provides access to relevant Pulp functionality
        @type  sync_conduit: L{pulp.server.content.conduits.repo_sync.RepoSyncConduit}

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @return: report of the details of the sync
        @rtype:  L{pulp.server.content.plugins.model.SyncReport}
        """
        raise NotImplementedError()

    def resolve_dependencies(self, repo, units, dependency_conduit, config):
        """
        Given a list of units, the importer will determine what other units in
        the repository represent their dependencies.

        The actual definition of what a "dependency" is depends on the content
        types in play. They may be dependencies for the unit to run or in the
        case of an aggregate unit (such as a group construct), a list of the
        units referenced by it.

        @param repo: describes the repository in which to search for dependencies
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param units: list of units to find dependencies for; entries in the list
               are of type
        @type  units: list of L{pulp.server.content.plugins.data.Unit}

        @param dependency_conduit: used to query into the server
        @type  dependency_conduit: L{pulp.server.content.conduits.dependency.DependencyResolutionConduit}

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @return: list of relevant units retrieved from the conduit calls; empty
                 list if no dependencies are found
        @rtype:  list of L{pulp.server.content.plugins.data.Unit}
        """
        raise NotImplementedError()

class GroupImporter(object):
    """
    Base class for Pulp content importers for a repository group. Group
    importers must subclass this class in order for Pulp to identify it as a
    valid importer during discovery.
    """

    # -- plugin lifecycle -----------------------------------------------------

    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this importer. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this importer. Must be unique
               across all group importers. Only letters and underscores are valid.
        * display_name - User-friendly identification of the importer.
        * types - List of all content type IDs that may be imported using this
               importer.

        This method call may be made multiple times during the course of a
        running Pulp server and thus should not be used for initialization
        purposes.

        @return: description of the importer's capabilities
        @rtype:  dict
        """
        raise NotImplementedError()
