# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import logging
from gettext import gettext as _
import errno
import shutil
import traceback
import csv

from pulp.common.plugins.progress import ProgressReport
from pulp.common.plugins.distributor_constants import MANIFEST_FILENAME
from pulp.plugins.distributor import Distributor


BUILD_DIRNAME = 'build'

logger = logging.getLogger(__name__)


class FileDistributor(Distributor):
    """
    Distribute files on the filesystem.
    """

    def __init__(self):
        super(FileDistributor, self).__init__()
        # Initialize instance variables used for writing out the metadata
        self.metadata_file = None
        self.metadata_csv_writer = None

    @classmethod
    def metadata(cls):
        """
        Advertise the capabilities of the mighty FileDistributor.

        :return: The description of the impressive FileDistributor's capabilities.
        :rtype:  dict
        """
        raise NotImplementedError()

    def distributor_removed(self, repo, config):
        """
        Delete the published files from our filesystem

        Please also see the superclass method definition for more documentation on this method.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        self.unpublish_repo(repo, config)

    def publish_repo(self, repo, publish_conduit, config):
        """
        Publish the repository.

        :param repo:            metadata describing the repo
        :type  repo:            pulp.plugins.model.Repository
        :param publish_conduit: The conduit for publishing a repo
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config:          plugin configuration
        :type  config:          pulp.plugins.config.PluginConfiguration
        :param config_conduit: Configuration Conduit;
        :type config_conduit: pulp.plugins.conduits.repo_validate.RepoConfigConduit
        :return:                report describing the publish operation
        :rtype:                 pulp.plugins.model.PublishReport
        """
        progress_report = FilePublishProgressReport(publish_conduit)
        logger.info(_('Beginning publish for repository <%(repo)s>') % {'repo': repo.id})

        try:
            progress_report.state = progress_report.STATE_IN_PROGRESS
            units = publish_conduit.get_units()

            # Set up an empty build_dir
            build_dir = os.path.join(repo.working_dir, BUILD_DIRNAME)
            # Let's erase the path at build_dir so we can be sure it's a clean directory
            self._rmtree_if_exists(build_dir)
            os.makedirs(build_dir)

            self.initialize_metadata(build_dir)

            try:
                # process each unit
                for unit in units:
                    links_to_create = self.get_paths_for_unit(unit)
                    self._symlink_unit(build_dir, unit, links_to_create)
                    self.publish_metadata_for_unit(unit)
            finally:
                #Finalize the processing
                self.finalize_metadata()

            # Let's unpublish, and then republish
            self.unpublish_repo(repo, config)

            hosting_locations = self.get_hosting_locations(repo, config)
            for location in hosting_locations:
                shutil.copytree(build_dir, location, symlinks=True)

            self.post_repo_publish(repo, config)

            # Clean up our build_dir
            self._rmtree_if_exists(build_dir)

            # Report that we are done
            progress_report.state = progress_report.STATE_COMPLETE
            return progress_report.build_final_report()
        except Exception, e:
            # Something failed. Let's put an error message on the report
            progress_report.error_message = str(e)
            progress_report.traceback = traceback.format_exc()
            progress_report.state = progress_report.STATE_FAILED
            report = progress_report.build_final_report()
            return report

    def unpublish_repo(self, repo, config):
        """
        Delete the published files from our filesystem

        Please also see the superclass method definition for more documentation on this method.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        hosting_locations = self.get_hosting_locations(repo, config)
        for location in hosting_locations:
            self._rmtree_if_exists(location)

    def validate_config(self, repo, config, config_conduit):
        raise NotImplementedError()

    def initialize_metadata(self, build_dir):
        """
        Initialize the metadata files that are going to be used for
        :param build_dir: The working directory where the new metadata should be generated
        :type build_dir: str
        """
        metadata_filename = os.path.join(build_dir, MANIFEST_FILENAME)
        self.metadata_file = open(metadata_filename, 'w')
        self.metadata_csv_writer = csv.writer(self.metadata_file)

    def publish_metadata_for_unit(self, unit):
        """
        Publish the metadata for a single unit.
        This should be writing to open file handles from the initialize_metadata call

        :param unit: the unit for which metadata needs to be generated
        :type unit: pulp.plugins.model.AssociatedUnit
        """
        self.metadata_csv_writer.writerow([unit.unit_key['name'], unit.unit_key['checksum'],
                                          unit.unit_key['size']])

    def finalize_metadata(self):
        """
        Do any work needed to finalize the metadata created from the initialize_metadata() or
        the publish_metadata_for_unit() calls.  Usually this will be closing file handles
        """
        self.metadata_file.close()

    def get_paths_for_unit(self, unit):
        """
        Get the paths within a target directory where this unit should be linked to

        :param unit: The unit for which we want to return target paths
        :type unit: pulp.plugins.model.AssociatedUnit
        :return: a list of paths the unit should be linked to
        :rtype: list of str
        """
        return [unit.unit_key['name'], ]

    def get_hosting_locations(self, repo, config):
        """
        Get the paths on the filesystem where the build directory should be copied

        :param repo: The repository that is going to be hosted
        :type repo: pulp.plugins.model.Repository
        :param config:    plugin configuration
        :type  config:    pulp.plugins.config.PluginConfiguration
        :return : list of paths on the filesystem where the build directory should be copied
        :rtype list of str
        """
        return []

    def post_repo_publish(self, repo, config):
        """
        API method that is called after the contents of a published repo have
        been moved into place on the filesystem

        :param repo: The repository that is going to be hosted
        :type repo: pulp.plugins.model.Repository
        :param config: the configuration for the repository
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        pass

    def _symlink_unit(self, build_dir, unit, target_paths):
        """
        For each unit, put a symlink in the build dir that points to its canonical location on disk.

        :param build_dir: The path on the local filesystem that we want to symlink the units into.
                          This path should already exist.
        :type  build_dir: basestring
        :param unit:     The unit to be symlinked
        :type  unit:     pulp.plugins.model.AssociatedUnit
        :param target_paths: The list of paths the unit should be symlinked to.
        :type  target_paths: list of L{str}
        """
        for target_path in target_paths:
            #symlink_filename = os.path.join(build_dir, unit.unit_key['name'])
            symlink_filename = os.path.join(build_dir, target_path)
            if os.path.exists(symlink_filename) or os.path.islink(symlink_filename):
                # There's already something there with the desired symlink filename. Let's try and
                # see if it points at the right thing. If it does, we don't need to do anything. If
                # it does not, we should remove what's there and add the correct symlink.
                try:
                    existing_link_path = os.readlink(symlink_filename)
                    if existing_link_path == unit.storage_path:
                        # We don't need to do anything more for this unit, move on to the next one
                        continue
                    # The existing symlink is incorrect, so let's remove it
                    os.remove(symlink_filename)
                except OSError, e:
                    # This will happen if we attempt to call readlink() on a file that wasn't a
                    # symlink.  We should remove the file and add the symlink. There error code
                    # should be EINVAL.  If it isn't, something else is wrong and we should raise.
                    if e.errno != errno.EINVAL:
                        raise e
                    # Remove the file that's at the symlink_filename path
                    os.remove(symlink_filename)
            # If we've gotten here, we've removed any existing file at the symlink_filename path,
            # so now we should recreate it.
            os.symlink(unit.storage_path, symlink_filename)

    def _rmtree_if_exists(self, path):
        """
        If the given path exists, remove it recursively. Else, do nothing.

        :param path: The path you want to recursively delete.
        :type  path: basestring
        """
        if os.path.exists(path):
            shutil.rmtree(path)


class FilePublishProgressReport(ProgressReport):
    """
    Used to carry the state of the publish run as it proceeds. This object is used
    to update the on going progress in Pulp at appropriate intervals through
    the update_progress call. Once the publish is finished, this object should
    be used to produce the final report to return to Pulp to describe the
    result of the operation.
    """
    # The following states can be set using the state() property
    STATE_IN_PROGRESS = 'in_progress'

    # A mapping of current states to allowed next states
    ALLOWED_STATE_TRANSITIONS = {
        ProgressReport.STATE_NOT_STARTED: (STATE_IN_PROGRESS, ProgressReport.STATE_FAILED),
        STATE_IN_PROGRESS: (ProgressReport.STATE_FAILED, ProgressReport.STATE_COMPLETE),
    }
