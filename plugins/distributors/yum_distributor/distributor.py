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

import gettext
import logging
import os
import traceback
import metadata

from pulp.server.content.plugins.distributor import Distributor
from pulp.server.content.plugins.model import PublishReport

# -- constants ----------------------------------------------------------------
_LOG = logging.getLogger(__name__)
_ = gettext.gettext

YUM_DISTRIBUTOR_TYPE_ID="yum_distributor"
RPM_TYPE_ID="rpm"
SRPM_TYPE_ID="srpm"
DRPM_TYPE_ID="drpm"
REQUIRED_CONFIG_KEYS = ["relative_url", "http", "https"]
OPTIONAL_CONFIG_KEYS = ["protected", "auth_cert", "auth_ca", 
                        "https_ca", "gpgkey", "generate_metadata",
                        "checksum_type", "metadata_types", "https_publish_dir"]

SUPPORTED_UNIT_TYPES = [RPM_TYPE_ID, SRPM_TYPE_ID, DRPM_TYPE_ID]
HTTPS_PUBLISH_DIR="/var/lib/pulp/published"
###
# Config Options Explained
###
# relative_url          - Relative URL to publish
#                         example: relative_url="rhel_6.2" may translate to publishing at
#                         http://localhost/pulp/repos/rhel_6.2
# http                  - True/False:  Publish through http
# https                 - True/False:  Publish through https
# protected             - True/False: Protect this repo with repo authentication
# auth_cert             - Certificate to use if repo authentication is required
# auth_ca               - CA to use if repo authentication is required
# https_ca              - CA to verify https communication
# gpgkey                - GPG Key associated with the packages in this repo
# generate_metadata     - True will run createrepo
#                         False will not run and uses existing metadata from sync
# checksum_type         - Checksum type to use for metadata generation
# metadata_types        - {'groups' : 1, 'updateinfo' : 1, 'prestodelta' : 1}: types to include or skip from metadata generation
# https_publish_dir     - Optional parameter to override the HTTPS_PUBLISH_DIR, mainly used for unit tests
# TODO:  Need to think some more about a 'mirror' option, how do we want to handle
# mirroring a remote url and not allowing any changes, what we were calling 'preserve_metadata' in v1.
#
# -- plugins ------------------------------------------------------------------

#
# TODO:
#   - Is this really a YumDistributor or should it be a HttpsDistributor?
#   - What if the relative_url changes between invocations, 
#    - How will we handle cleanup of the prior publish path/symlink
class YumDistributor(Distributor):


    @classmethod
    def metadata(cls):
        return {
            'id'           : YUM_DISTRIBUTOR_TYPE_ID,
            'display_name' : 'Yum Distributor',
            'types'        : [RPM_TYPE_ID, SRPM_TYPE_ID]
        }

    def validate_config(self, repo, config):
        _LOG.info("validate_config invoked, config values are: %s" % (config.repo_plugin_config))
        for key in REQUIRED_CONFIG_KEYS:
            if key not in config.repo_plugin_config:
                msg = _("Missing required configuration key: %(key)s" % {"key":key})
                _LOG.error(msg)
                return False, msg
        for key in config.repo_plugin_config:
            if key not in REQUIRED_CONFIG_KEYS and key not in OPTIONAL_CONFIG_KEYS:
                msg = _("Configuration key '%(key)s' is not supported" % {"key":key})
                _LOG.error(msg)
                return False, msg
        # If overriding https publish dir, be sure it exists and we can write to it
        if config.repo_plugin_config.has_key("https_publish_dir"):
            publish_dir = config.repo_plugin_config["https_publish_dir"]
            if not os.path.exists(publish_dir) or not os.path.isdir(publish_dir):
                msg = _("Value for 'https_publish_dir' is not an existing directory: %(publish_dir)s" % {"publish_dir":publish_dir})
                return False, msg
            if not os.access(publish_dir, os.R_OK) or not os.access(publish_dir, os.W_OK):
                msg = _("Unable to read & write to specified 'https_publish_dir': %(publish_dir)s" % {"publish_dir":publish_dir})
                return False, msg
        ##
        # TODO: Need to add a check for the Repo's relativepath
        ##
        return True, None

    def get_https_publish_dir(self, config=None):
        """
        @param config
        @type pulp.server.content.plugins.config.PluginCallConfiguration

        """
        if config:
            if config.repo_plugin_config.has_key("https_publish_dir"):
                publish_dir = config.repo_plugin_config["https_publish_dir"]
                _LOG.info("Override HTTPS publish directory from passed in config value to: %s" % (publish_dir))
                return publish_dir
        return HTTPS_PUBLISH_DIR

    def get_repo_relative_path(self, repo, config):
        relative_url = config.get("relative_url")
        if relative_url:
            return relative_url
        return repo.id

    def publish_repo(self, repo, publish_conduit, config):
        summary = {}
        details = {}
        # Determine Content in this repo
        unfiltered_units = publish_conduit.get_units()
        # Remove unsupported units
        units = filter(lambda u: u.type_id in SUPPORTED_UNIT_TYPES, unfiltered_units)
        _LOG.info("Publish on %s invoked. %s existing units, %s of which are supported to be published." \
                % (repo.id, len(unfiltered_units), len(units)))
        # Create symlinks under repo.working_dir
        status, errors = self.handle_symlinks(units, repo.working_dir)
        if not status:
            _LOG.error("Unable to publish %s items" % (len(errors)))
        # update/generate metadata for the published repo
        metadata.generate_metadata(repo, config)
        # Publish for HTTPS 
        #  Create symlink for repo.working_dir where HTTPS gets served
        #  Should we consider HTTP?
        https_publish_dir = self.get_https_publish_dir(config)
        relpath = self.get_repo_relative_path(repo, config)
        if relpath.startswith("/"):
            relpath = relpath[1:]
        _LOG.info("Using https_publish_dir: %s, relative path: %s" % (https_publish_dir, relpath))
        repo_publish_dir = os.path.join(https_publish_dir, "repos", relpath)
        _LOG.info("Publishing repo <%s> to <%s>" % (repo.id, repo_publish_dir))
        self.create_symlink(repo.working_dir, repo_publish_dir)

        # TODO: RepoAuth:
        #  Where do we store RepoAuth credentials?
        #
        summary["repo_publish_dir"] = repo_publish_dir
        summary["num_units_attempted"] = len(units)
        summary["num_units_published"] = len(units) - len(errors)
        summary["num_units_errors"] = len(errors)
        details["errors"] = errors
        _LOG.info("Publish complete:  summary = <%s>, details = <%s>" % (summary, details))
        if errors:
            return publish_conduit.build_failure_report(summary, details)
        return publish_conduit.build_success_report(summary, details)

    def handle_symlinks(self, units, symlink_dir):
        """
        @param units list of units that belong to the repo and should be published
        @type units [AssociatedUnit]

        @param symlink_dir where to create symlinks 
        @type symlink_dir str
        
        @return tuple of status and list of error messages if any occurred 
        @rtype (bool, [str])
        """
        _LOG.info("handle_symlinks invoked with %s units to %s dir" % (len(units), symlink_dir))
        errors = []
        for u in units:
            # Skip errata...it will be published through repo metadata 'updateinfo'
            relpath = self.get_relpath_from_unit(u)
            source_path = u.storage_path
            symlink_path = os.path.join(symlink_dir, relpath)
            if not os.path.exists(source_path):
                msg = "Source path: %s is missing" % (source_path)
                errors.append((source_path, symlink_path, msg))
                continue
            _LOG.info("Unit exists at: %s we need to symlink to: %s" % (source_path, symlink_path))
            try:
                if not self.create_symlink(source_path, symlink_path):
                    msg = "Unable to create symlink for: %s pointing to %s" % (symlink_path, source_path)
                    _LOG.error(msg)
                    errors.append((source_path, symlink_path, msg))
                    continue
            except Exception, e:
                tb_info = traceback.format_exc()
                _LOG.error("%s" % (tb_info))
                _LOG.critical(e)
                errors.append((source_path, symlink_path, str(e)))
                continue
        if errors:
            return False, errors
        return True, []

    def get_relpath_from_unit(self, unit):
        """
        @param unit
        @type AssociatedUnit

        @return relative path
        @rtype str
        """
        filename = ""
        if unit.metadata.has_key("relativepath"):
            relpath = unit.metadata["relativepath"]
        elif unit.metadata.has_key("filename"):
            relpath = unit.metadata["filename"]
        elif unit.metadata.has_key("fileName"):
            relpath = unit.metadata["fileName"]
        else:
            relpath = os.path.basename(unit.storage_path)
        return relpath

    def create_symlink(self, source_path, symlink_path):
        """
        @param source_path source path 
        @type source_path str

        @param symlink_path path of where we want the symlink to reside
        @type symlink_path str

        @return True on success, False on error
        @rtype bool
        """
        if symlink_path.endswith("/"):
            symlink_path = symlink_path[:-1]
        if os.path.lexists(symlink_path):
            if not os.path.islink(symlink_path):
                _LOG.error("%s is not a symbolic link as expected." % (symlink_path))
                return False
            existing_link_target = os.readlink(symlink_path)
            if existing_link_target == source_path:
                return True
            _LOG.warning("Removing <%s> since it was pointing to <%s> and not <%s>" \
                    % (symlink_path, existing_link_target, source_path))
            os.unlink(symlink_path)
        # Account for when the relativepath consists of subdirectories
        if not self.create_dirs(os.path.dirname(symlink_path)):
            return False
        _LOG.debug("creating symlink %s pointing to %s" % (symlink_path, source_path))
        # TODO:
        #  Need to handle conflicts when a subdirectory already exists
        #  Or what happens if another repo has published into this path already
        os.symlink(source_path, symlink_path)
        return True

    def create_dirs(self, target):
        """
        @param target path
        @type target str

        @return True - success, False - error
        @rtype bool
        """
        try:
            os.makedirs(target)
        except OSError, e:
            # Another thread may have created the dir since we checked,
            # if that's the case we'll see errno=17, so ignore that exception
            if e.errno != 17:
                _LOG.error("Unable to create directories for: %s" % (target))
                tb_info = traceback.format_exc()
                _LOG.error("%s" % (tb_info))
                return False
        return True

