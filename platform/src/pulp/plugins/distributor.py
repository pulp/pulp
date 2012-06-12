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


class Distributor(object):
    """
    Base class for Pulp content distributors. Distributors must subclass this
    class in order for Pulp to identify it as a valid distributor during
    discovery.
    """

    # -- plugin lifecycle -----------------------------------------------------

    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this distributor. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this distributor. Must be unique
               across all distributors. Only letters and underscores are valid.
        * display_name - User-friendly identification of the distributor.
        * types - List of all content type IDs that may be imported using this
               distributor.

        This method call may be made multiple times during the course of a
        running Pulp server and thus should not be used for initialization
        purposes.

        @return: description of the distributor's capabilities
        @rtype:  dict
        """
        raise NotImplementedError()

    # -- repo lifecycle -------------------------------------------------------

    def validate_config(self, repo, config, related_repos):
        """
        Allows the distributor to check the contents of a potential configuration
        for the given repository. This call is made both for the addition of
        this distributor to a new repository as well as updating the configuration
        for this distributor on a previously configured repository. The implementation
        should use the given repository data to ensure that updating the
        configuration does not put the repository into an inconsistent state.

        The return is a tuple of the result of the validation (True for success,
        False for failure) and a message. The message may be None and is unused
        in the success case. For a failed validation, the message will be
        communicated to the caller so the plugin should take i18n into
        consideration when generating the message.

        The related_repos parameter contains a list of other repositories that
        have a configured distributor of this type. The distributor configurations
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

    def distributor_added(self, repo, config):
        """
        Called upon the successful addition of a distributor of this type to a
        repository. This hook allows the distributor to do any initial setup
        it needs to prior to the first publish call.

        This call should raise an exception in the case where the distributor is
        unable to successfully perform any setup actions that will be required
        to perform actions (publish, unpublish) later. In this case, Pulp will
        mark the distributor as broken and repository operations that rely on
        the distributor will be unavailable for the given repository.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}
        """
        pass

    def distributor_removed(self, repo, config):
        """
        Called when a distributor of this type is removed from a repository.
        This hook allows the distributor to clean up any files that may have
        been created during the actual publishing.

        The distributor may use the contents of the working directory in cleanup.
        It is not required that the contents of this directory be deleted by
        the distributor; Pulp will ensure it is wiped following this call.

        If this call raises an exception, the distributor will still be removed
        from the repository and the working directory contents will still be
        wiped by Pulp.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}
        """
        pass

    # -- actions --------------------------------------------------------------

    def publish_repo(self, repo, publish_conduit, config):
        """
        Publishes the given repository.

        While this call may be implemented using multiple threads, its execution
        from the Pulp server's standpoint should be synchronous. This call should
        not return until the publish is complete.

        It is not expected that this call be atomic. Should an error occur, it
        is not the responsibility of the distributor to rollback any changes
        that have been made.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param publish_conduit: provides access to relevant Pulp functionality
        @type  publish_conduit: L{pulp.server.content.conduits.repo_publish.RepoPublishConduit}

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginConfiguration}
        """
        raise NotImplementedError()

    def create_consumer_payload(self, repo, config):
        """
        Called when a consumer binds to a repository using this distributor.
        This call should return a dictionary describing all data the consumer
        will need to access the repository. The contents will vary wildly
        depending on the method the repository is published, but examples
        of returned data includes authentication information, location of the
        repository (e.g. URL), and data required to verify the contents
        of the published repository.

        @param repo: metadata describing the repository
        @type  repo: L{pulp.server.content.plugins.data.Repository}

        @param config: plugin configuration
        @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

        @return: dictionary of relevant data
        @rtype:  dict
        """
        return {}