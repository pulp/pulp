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
import shutil
import time
import traceback
import urlparse
import metadata
from pulp.repo_auth import repo_cert_utils, protected_repo_utils
from pulp.yum_plugin import util
from pulp.server.content.plugins.distributor import Distributor
from ConfigParser import SafeConfigParser
# -- constants ----------------------------------------------------------------
_LOG = logging.getLogger(__name__)
_ = gettext.gettext

YUM_DISTRIBUTOR_TYPE_ID="yum_distributor"
RPM_TYPE_ID="rpm"
SRPM_TYPE_ID="srpm"
DRPM_TYPE_ID="drpm"
DISTRO_TYPE_ID="distribution"
ERRATA_TYPE_ID="erratum"
REQUIRED_CONFIG_KEYS = ["relative_url", "http", "https"]
OPTIONAL_CONFIG_KEYS = ["protected", "auth_cert", "auth_ca", 
                        "https_ca", "gpgkey", "generate_metadata",
                        "checksum_type", "skip_content_types", "https_publish_dir", "http_publish_dir"]

SUPPORTED_UNIT_TYPES = [RPM_TYPE_ID, SRPM_TYPE_ID, DRPM_TYPE_ID, DISTRO_TYPE_ID]
HTTP_PUBLISH_DIR="/var/lib/pulp/published/http/repos"
HTTPS_PUBLISH_DIR="/var/lib/pulp/published/https/repos"
CONFIG_REPO_AUTH="/etc/pulp/repo_auth.conf"
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
# skip_content_types    - List of what content types to skip during sync, options:
#                         ["rpm", "drpm", "errata", "distribution", "packagegroup"]
# https_publish_dir     - Optional parameter to override the HTTPS_PUBLISH_DIR, mainly used for unit tests
# http_publish_dir      - Optional parameter to override the HTTP_PUBLISH_DIR, mainly used for unit tests
# TODO:  Need to think some more about a 'mirror' option, how do we want to handle
# mirroring a remote url and not allowing any changes, what we were calling 'preserve_metadata' in v1.
#
# -- plugins ------------------------------------------------------------------

#
# TODO:
#   - Need an unpublish to remove a link, think when a repo is deleted we still keep the symlink under the published dir
#   - Is this really a YumDistributor or should it be a HttpsDistributor?
#   - What if the relative_url changes between invocations,
#    - How will we handle cleanup of the prior publish path/symlink
class YumDistributor(Distributor):

    def __init__(self):
        super(YumDistributor, self).__init__()
        self.canceled = False

    @classmethod
    def metadata(cls):
        return {
            'id'           : YUM_DISTRIBUTOR_TYPE_ID,
            'display_name' : 'Yum Distributor',
            'types'        : [RPM_TYPE_ID, SRPM_TYPE_ID]
        }

    def validate_config(self, repo, config, related_repos):
        _LOG.info("validate_config invoked, config values are: %s" % (config.repo_plugin_config))
        auth_cert_bundle = {}
        for key in REQUIRED_CONFIG_KEYS:
            value = config.get(key)
            if value is None:
                msg = _("Missing required configuration key: %(key)s" % {"key":key})
                _LOG.error(msg)
                return False, msg
            if key == 'relative_url':
                relative_path = config.get('relative_url')
                if relative_path is not None and not isinstance(relative_path, basestring):
                    msg = _("relative_url should be a basestring; got %s instead" % relative_path)
                    _LOG.error(msg)
                    return False, msg
            if key == 'http':
                config_http = config.get('http')
                if config_http is not None and not isinstance(config_http, bool):
                    msg = _("http should be a boolean; got %s instead" % config_http)
                    _LOG.error(msg)
                    return False, msg
            if key == 'https':
                config_https = config.get('https')
                if config_https is not None and not isinstance(config_https, bool):
                    msg = _("https should be a boolean; got %s instead" % config_https)
                    _LOG.error(msg)
                    return False, msg
        for key in config.keys():
            if key not in REQUIRED_CONFIG_KEYS and key not in OPTIONAL_CONFIG_KEYS:
                msg = _("Configuration key '%(key)s' is not supported" % {"key":key})
                _LOG.error(msg)
                return False, msg
            if key == 'protected':
                protected = config.get('protected')
                if protected is not None and not isinstance(protected, bool):
                    msg = _("protected should be a boolean; got %s instead" % protected)
                    _LOG.error(msg)
                    return False, msg
            if key == 'generate_metadata':
                generate_metadata = config.get('generate_metadata')
                if generate_metadata is not None and not isinstance(generate_metadata, bool):
                    msg = _("generate_metadata should be a boolean; got %s instead" % generate_metadata)
                    _LOG.error(msg)
                    return False, msg
            if key == 'checksum_type':
                checksum_type = config.get('checksum_type')
                if checksum_type is not None and not util.is_valid_checksum_type(checksum_type):
                    msg = _("%s is not a valid checksum type" % checksum_type)
                    _LOG.error(msg)
                    return False, msg
            if key == 'skip_content_types':
                metadata_types = config.get('skip_content_types')
                if metadata_types is not None and not isinstance(metadata_types, list):
                    msg = _("skip_content_types should be a dictionary; got %s instead" % metadata_types)
                    _LOG.error(msg)
                    return False, msg
            if key == 'auth_cert':
                auth_pem = config.get('auth_cert').encode('utf-8')
                if auth_pem is not None and not util.validate_cert(auth_pem):
                    msg = _("auth_cert is not a valid certificate")
                    _LOG.error(msg)
                    return False, msg
                auth_cert_bundle['cert'] = auth_pem
            if key == 'auth_ca':
                auth_ca = config.get('auth_ca').encode('utf-8')
                if auth_ca is not None and not util.validate_cert(auth_ca):
                    msg = _("auth_ca is not a valid certificate")
                    _LOG.error(msg)
                    return False, msg
                auth_cert_bundle['ca'] = auth_ca
        # process auth certs
        repo_relative_path = self.get_repo_relative_path(repo, config)
        if repo_relative_path.startswith("/"):
            repo_relative_path = repo_relative_path[1:]
        self.process_repo_auth_certificate_bundle(repo.id, repo_relative_path, auth_cert_bundle)
        # If overriding https publish dir, be sure it exists and we can write to it
        publish_dir = config.get("https_publish_dir")
        if publish_dir:
            if not os.path.exists(publish_dir) or not os.path.isdir(publish_dir):
                msg = _("Value for 'https_publish_dir' is not an existing directory: %(publish_dir)s" % {"publish_dir":publish_dir})
                return False, msg
            if not os.access(publish_dir, os.R_OK) or not os.access(publish_dir, os.W_OK):
                msg = _("Unable to read & write to specified 'https_publish_dir': %(publish_dir)s" % {"publish_dir":publish_dir})
                return False, msg
        publish_dir = config.get("http_publish_dir")
        if publish_dir:
            if not os.path.exists(publish_dir) or not os.path.isdir(publish_dir):
                msg = _("Value for 'http_publish_dir' is not an existing directory: %(publish_dir)s" % {"publish_dir":publish_dir})
                return False, msg
            if not os.access(publish_dir, os.R_OK) or not os.access(publish_dir, os.W_OK):
                msg = _("Unable to read & write to specified 'http_publish_dir': %(publish_dir)s" % {"publish_dir":publish_dir})
                return False, msg
        rel_url =  config.get("relative_url")
        if rel_url:
            conflict_status, conflict_msg = self.does_rel_url_conflict(rel_url, related_repos)
            if conflict_status:
                _LOG.info(conflict_msg)
                return False, conflict_msg
        return True, None

    def init_progress(self):
        return  {
            "state": "IN_PROGRESS",
            "num_success" : 0,
            "num_error" : 0,
            "items_left" : 0,
            "items_total" : 0,
            "error_details" : [],
        }

    def process_repo_auth_certificate_bundle(self, repo_id, repo_relative_path, cert_bundle):
        """
        Write the cert bundle to location specified in the repo_auth.conf;
        also updates the protected_repo_listings file with repo info. If
        no cert bundle, delete any orphaned repo info from listings.

        @param repo_id: repository id
        @type repo_id: str

        @param repo_relative_path: repo relative path
        @type  repo_relative_path: str

        @param cert_bundle: mapping of item to its PEM encoded contents
        @type  cert_bundle: dict {str, str}
        """

        repo_auth_config = load_config()
        repo_cert_utils_obj = repo_cert_utils.RepoCertUtils(repo_auth_config)
        protected_repo_utils_obj = protected_repo_utils.ProtectedRepoUtils(repo_auth_config)

        if cert_bundle:
            repo_cert_utils_obj.write_consumer_cert_bundle(repo_id, cert_bundle)
            # add repo to protected list
            protected_repo_utils_obj.add_protected_repo(repo_relative_path, repo_id)
        else:
            # remove stale info, if any
            protected_repo_utils_obj.delete_protected_repo(repo_relative_path)

    def does_rel_url_conflict(self, rel_url, related_repos):
        """
        @param rel_url
        @type rel_url: str

        @param related_repos
        @type related_repos: L{pulp.server.content.plugins.model.RelatedRepository}

        @return True, msg - conflict found,  False, None - no conflict found
        @rtype bool, msg
        """
        existing_rel_urls = self.form_rel_url_lookup_table(related_repos)
        current_url_pieces = self.split_path(rel_url)
        temp_lookup = existing_rel_urls
        for piece in current_url_pieces:
            if not temp_lookup.has_key(piece):
                break
            temp_lookup = temp_lookup[piece]
        if temp_lookup.has_key("repo_id"):
            msg = _("Relative url '%(rel_url)s' conflicts with existing relative_url of '%(conflict_rel_url)s' from repo '%(conflict_repo_id)s'" \
                    % {"rel_url":rel_url, "conflict_rel_url":temp_lookup["url"], "conflict_repo_id":temp_lookup["repo_id"]})
            return True, msg
        return False, None

    def split_path(self, path):
        pieces = []
        temp_pieces = path.split("/")
        for p in temp_pieces:
            if p:
                pieces.append(p)
        return pieces

    def form_rel_url_lookup_table(self, repos):
        """
        @param repos:
        @type L{pulp.server.content.plugins.model.RelatedRepository}

        @return a dictionary to serve as a lookup table
        @rtype: dict

        Format:
         {"path_component_1": {"path_component_2": {"repo_id":"id"}}}
        Example:
            /pub/rhel/el5/i386
            /pub/rhel/el5/x86_64
            /pub/rhel/el6/i386
            /pub/rhel/el6/x86_64

         {"pub": {
            "rhel": {"el5": {
                            "i386": {"repo_id":"rhel_el5_i386", "url":"/pub/rhel/el5/i386" }
                            "x86_64": {"repod_id":"rhel_el5_x86_64", "url":"/pub/rhel/el5/x86_64"})
                    "el6":{
                            "i386": { "repo_id":"rhel_el6_i386", "url":"/pub/rhel/el6/i386"}
                            "x86_64": { "repo_id":"rhel_el6_x86_64", "url":"/pub/rhel/el6/x86_64"}}
                }}}

        """
        # We will construct a tree like data object referenced by the lookup dict
        # Each piece of a url will be used to create a new dict
        # When we get to the end of the url pieces we will store 
        # a single key/value pair of 'repo_id':"id"
        # The existance of this key/value pair signifies a conflict
        #  Desire is to support similar subdirs
        #  ...yet avoid the chance of a new repo conflicting with an already established repo's subdir
        lookup = {}
        if not repos:
            return lookup
        for r in repos:
            if not r.plugin_configs:
                continue
            # It's possible that multiple instances of a Distributor could be associated
            # to a RelatedRepository.  At this point we don't intend to support that so we will
            # assume that we only use the first instance of the config
            # Note: ...Pulp will be sure to only pass us plugin_configs which relate to our distributor type
            related_config = r.plugin_configs[0]
            rel_url = self.get_repo_relative_path(r, related_config)
            if not rel_url:
                continue
            url_pieces = self.split_path(rel_url)
            if not url_pieces:
                # Skip this repo since we didn't find any url pieces to process
                continue
            temp_lookup = lookup
            for piece in url_pieces:
                if not temp_lookup.has_key(piece):
                    temp_lookup[piece] = {}
                temp_lookup = temp_lookup[piece]
            if len(temp_lookup.keys()) != 0:
                # We expect these exceptions should never occur, since validate_config is called before accepting any repo
                # ...yet in the case something goes wrong we enforce these checks and thrown an exception
                msg = _("Relative URL lookup table encountered a conflict with repo <%(repo_id)s> with relative_url <%(rel_url)s> broken into %(pieces)s.\n") % \
                        {"repo_id":r.id, "rel_url":rel_url, "pieces":url_pieces}
                if temp_lookup.has_key("repo_id"):
                    msg += _("This repo <%(repo_id)s> conflicts with repo <%(conflict_repo_id)s>") % {"repo_id":r.id, "conflict_repo_id":temp_lookup["repo_id"]}
                    _LOG.error(msg)
                    raise Exception(msg)
                # Unexpected occurence, raise an exception
                msg += _("This repo <%(repo_id)s> conflicts with an existing repos sub directories, specific sub dirs of conflict are %(sub_dirs)s") \
                        % {"repo_id":r.id, "sub_dirs":temp_lookup}
                _LOG.error(msg)
                raise Exception(msg)
            # Note:  We are storing both repo_id and rel_url at the root of each path to make it easier to repo
            # the repo/relative_url occupying this space when a conflict is detected.
            temp_lookup["repo_id"] = r.id
            temp_lookup["url"] = rel_url
        return lookup

    def get_http_publish_dir(self, config=None):
        """
        @param config
        @type pulp.server.content.plugins.config.PluginCallConfiguration
        """
        if config:
            publish_dir = config.get("http_publish_dir")
            if publish_dir:
                _LOG.info("Override HTTP publish directory from passed in config value to: %s" % (publish_dir))
                return publish_dir
        return HTTP_PUBLISH_DIR

    def get_https_publish_dir(self, config=None):
        """
        @param config
        @type pulp.server.content.plugins.config.PluginCallConfiguration
        """
        if config:
            publish_dir = config.get("https_publish_dir")
            if publish_dir:
                _LOG.info("Override HTTPS publish directory from passed in config value to: %s" % (publish_dir))
                return publish_dir
        return HTTPS_PUBLISH_DIR

    def get_repo_relative_path(self, repo, config):
        relative_url = config.get("relative_url")
        if relative_url:
            return relative_url
        return repo.id

    def cancel_publish_repo(self, repo):
        self.canceled = True
        return metadata.cancel_createrepo(repo.working_dir)

    def publish_repo(self, repo, publish_conduit, config):
        summary = {}
        details = {}
        progress_status = {
            "packages":           {"state": "NOT_STARTED"},
            "distribution":       {"state": "NOT_STARTED"},
            "metadata":           {"state": "NOT_STARTED"},
            "publish_http":       {"state": "NOT_STARTED"},
            "publish_https":      {"state": "NOT_STARTED"},
            }

        def progress_callback(type_id, status):
            progress_status[type_id] = status
            publish_conduit.set_progress(progress_status)

        if self.canceled:
            return publish_conduit.build_failure_report(summary, details)
        # Determine Content in this repo
        unfiltered_units = publish_conduit.get_units()
        # filter compatible units
        units = filter(lambda u: u.type_id not in [DISTRO_TYPE_ID, ERRATA_TYPE_ID], unfiltered_units)
        _LOG.info("Publish on %s invoked. %s existing units, %s of which are supported to be published." \
                % (repo.id, len(unfiltered_units), len(units)))
        # Create symlinks under repo.working_dir
        status, errors = self.handle_symlinks(units, repo.working_dir, progress_callback)
        if not status:
            _LOG.error("Unable to publish %s items" % (len(errors)))
        # symlink distribution files if any under repo.working_dir
        distro_units = filter(lambda u: u.type_id == DISTRO_TYPE_ID, unfiltered_units)
        distro_status, distro_errors = self.symlink_distribution_unit_files(distro_units, repo.working_dir, progress_callback)
        if not distro_status:
            _LOG.error("Unable to publish distribution tree %s items" % (len(errors)))
        # update/generate metadata for the published repo
        repo_scratchpad = publish_conduit.get_repo_scratchpad()
        src_working_dir = ''
        if repo_scratchpad.has_key("importer_working_dir"):
            src_working_dir = repo_scratchpad['importer_working_dir']

        if self.canceled:
            return publish_conduit.build_failure_report(summary, details)
        metadata_start_time = time.time()
        self.copy_importer_repodata(src_working_dir, repo.working_dir)
        metadata_status, metadata_errors = metadata.generate_metadata(repo, publish_conduit, config, progress_callback)
        metadata_end_time = time.time()
        relpath = self.get_repo_relative_path(repo, config)
        if relpath.startswith("/"):
            relpath = relpath[1:]
        #
        # Handle publish link for HTTPS
        #
        https_publish_dir = self.get_https_publish_dir(config)
        https_repo_publish_dir = os.path.join(https_publish_dir, relpath).rstrip('/')
        if config.get("https"):
            # Publish for HTTPS
            self.set_progress("publish_https", {"state" : "IN_PROGRESS"}, progress_callback)
            try:
                _LOG.info("HTTPS Publishing repo <%s> to <%s>" % (repo.id, https_repo_publish_dir))
                self.create_symlink(repo.working_dir, https_repo_publish_dir)
                summary["https_publish_dir"] = https_repo_publish_dir
                self.set_progress("publish_https", {"state" : "FINISHED"}, progress_callback)
            except:
                self.set_progress("publish_https", {"state" : "FAILED"}, progress_callback)
        else:
            self.set_progress("publish_https", {"state" : "SKIPPED"}, progress_callback)
            if os.path.lexists(https_repo_publish_dir):
                _LOG.debug("Removing link for %s since https is not set" % https_repo_publish_dir)
                self.remove_symlink(https_publish_dir, https_repo_publish_dir)
        #
        # Handle publish link for HTTP
        #
        http_publish_dir = self.get_http_publish_dir(config)
        http_repo_publish_dir = os.path.join(http_publish_dir, relpath).rstrip('/')
        if config.get("http"):
            # Publish for HTTP
            self.set_progress("publish_http", {"state" : "IN_PROGRESS"}, progress_callback)
            try:
                _LOG.info("HTTP Publishing repo <%s> to <%s>" % (repo.id, http_repo_publish_dir))
                self.create_symlink(repo.working_dir, http_repo_publish_dir)
                summary["http_publish_dir"] = http_repo_publish_dir
                self.set_progress("publish_http", {"state" : "FINISHED"}, progress_callback)
            except:
                self.set_progress("publish_http", {"state" : "FAILED"}, progress_callback)
        else:
            self.set_progress("publish_http", {"state" : "SKIPPED"}, progress_callback)
            if os.path.lexists(http_repo_publish_dir):
                _LOG.debug("Removing link for %s since http is not set" % http_repo_publish_dir)
                self.remove_symlink(http_publish_dir, http_repo_publish_dir)

        summary["num_package_units_attempted"] = len(units)
        summary["num_package_units_published"] = len(units) - len(errors)
        summary["num_package_units_errors"] = len(errors)
        summary["num_distribution_units_attempted"] = len(distro_units)
        summary["num_distribution_units_published"] = len(distro_units) - len(distro_errors)
        summary["num_distribution_units_errors"] = len(distro_errors)
        summary["relative_path"] = relpath
        if metadata_status is False and not len(metadata_errors):
            summary["skip_metadata_update"] = True
        else:
            summary["skip_metadata_update"] = False
        details["errors"] = errors + distro_errors + metadata_errors
        details['time_metadata_sec'] = metadata_end_time - metadata_start_time
        # metadata generate skipped vs run
        _LOG.info("Publish complete:  summary = <%s>, details = <%s>" % (summary, details))
        if errors:
            return publish_conduit.build_failure_report(summary, details)
#        _LOG.info("Publish progress information %s" % publish_conduit.progress_report)
        return publish_conduit.build_success_report(summary, details)

    def distributor_removed(self, repo, config):
        # clean up any repo specific data
        repo_auth_config = load_config()
        repo_cert_utils_obj = repo_cert_utils.RepoCertUtils(repo_auth_config)
        protected_repo_utils_obj = protected_repo_utils.ProtectedRepoUtils(repo_auth_config)
        repo_relative_path = self.get_repo_relative_path(repo, config)
        if repo_relative_path.startswith("/"):
            repo_relative_path = repo_relative_path[1:]
        repo_cert_utils_obj.delete_for_repo(repo.id)
        protected_repo_utils_obj.delete_protected_repo(repo_relative_path)

    def set_progress(self, type_id, status, progress_callback=None):
        if progress_callback:
            progress_callback(type_id, status)

    def handle_symlinks(self, units, symlink_dir, progress_callback=None):
        """
        @param units list of units that belong to the repo and should be published
        @type units [AssociatedUnit]

        @param symlink_dir where to create symlinks 
        @type symlink_dir str

        @param progress_callback: callback to report progress info to publish_conduit
        @type  progress_callback: function

        @return tuple of status and list of error messages if any occurred 
        @rtype (bool, [str])
        """
        packages_progress_status = self.init_progress()
        _LOG.info("handle_symlinks invoked with %s units to %s dir" % (len(units), symlink_dir))
        self.set_progress("packages", packages_progress_status, progress_callback)
        errors = []
        packages_progress_status["items_total"] = len(units)
        packages_progress_status["items_left"] =  len(units)
        for u in units:
            self.set_progress("packages", packages_progress_status, progress_callback)
            relpath = self.get_relpath_from_unit(u)
            source_path = u.storage_path
            symlink_path = os.path.join(symlink_dir, relpath)
            if not os.path.exists(source_path):
                msg = "Source path: %s is missing" % (source_path)
                errors.append((source_path, symlink_path, msg))
                packages_progress_status["num_error"] += 1
                packages_progress_status["items_left"] -= 1
                continue
            _LOG.info("Unit exists at: %s we need to symlink to: %s" % (source_path, symlink_path))
            try:
                if not self.create_symlink(source_path, symlink_path):
                    msg = "Unable to create symlink for: %s pointing to %s" % (symlink_path, source_path)
                    _LOG.error(msg)
                    errors.append((source_path, symlink_path, msg))
                    packages_progress_status["num_error"] += 1
                    packages_progress_status["items_left"] -= 1
                    continue
                packages_progress_status["num_success"] += 1
            except Exception, e:
                tb_info = traceback.format_exc()
                _LOG.error("%s" % (tb_info))
                _LOG.critical(e)
                errors.append((source_path, symlink_path, str(e)))
                packages_progress_status["num_error"] += 1
                packages_progress_status["items_left"] -= 1
                continue
            packages_progress_status["items_left"] -= 1
        if errors:
            packages_progress_status["error_details"] = errors
            return False, errors
        packages_progress_status["state"] = "FINISHED"
        self.set_progress("packages", packages_progress_status, progress_callback)
        return True, []

    def remove_symlink(self, publish_dir, link_path):
        """
        @param publish_dir: full http/https publish directory for all repos
        @type publish_dir: str

        @param link_path: full publish path for this specific repo
        @type link_path: str

        Intent is to remove all the specific link and all unique sub directories used to create it
        """
        # Remove the symlink from filesystem
        link_path = link_path.rstrip('/')
        os.unlink(link_path)

        # Adjust the link_path and removal the symlink from it
        link_path = os.path.split(link_path)[0]
        common_pieces = [x for x in publish_dir.split('/') if x] # remove empty pieces
        link_pieces = [x for x in link_path.split('/') if x]
        # Determine what are the non shared pieces from this link
        potential_to_remove = link_pieces[len(common_pieces):]
        num_pieces = len(potential_to_remove)
        # Start removing the end pieces of the path and work our way back
        # If we encounter a non-empty directory stop removal and return
        for index in range(num_pieces, 0, -1):
            path_to_remove = os.path.join(publish_dir, *potential_to_remove[:index])  #Start with all then work back
            if len(os.listdir(path_to_remove)):
                # Directory is not empty so stop removal quit
                break
            os.rmdir(path_to_remove)

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
        elif unit.unit_key.has_key("fileName"):
            relpath = unit.unit_key["fileName"]
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

    def copy_importer_repodata(self, src_working_dir, tgt_working_dir):
        """
        @param src_working_dir importer repo working dir where repodata dir exists
        @type src_working_dir str

        @param tgt_working_dir importer repo working dir where repodata dir needs to be copied
        @type tgt_working_dir str

        @return True - success, False - error
        @rtype bool
        """
        try:
            src_repodata_dir = os.path.join(src_working_dir, "repodata")
            if not os.path.exists(src_repodata_dir):
                _LOG.debug("No repodata dir to copy at %s" % src_repodata_dir)
                return False
            tgt_repodata_dir = os.path.join(tgt_working_dir, "repodata")
            if os.path.exists(tgt_repodata_dir):
                shutil.rmtree(tgt_repodata_dir)
            shutil.copytree(src_repodata_dir, tgt_repodata_dir)
        except (IOError, OSError):
            _LOG.error("Unable to copy repodata directory from %s to %s" % (src_working_dir, tgt_working_dir))
            tb_info = traceback.format_exc()
            _LOG.error("%s" % (tb_info))
            return False
        _LOG.info("Copied repodata from %s to %s" % (src_working_dir, tgt_working_dir))
        return True

    def symlink_distribution_unit_files(self, units, symlink_dir, progress_callback=None):
        """
        Publishing distriubution unit involves publishing files underneath the unit.
        Distribution is an aggregate unit with distribution files. This call
        looksup each distribution unit and symlinks the files from the storage location
        to working directory.

        @param units
        @type AssociatedUnit

        @param symlink_dir: path of where we want the symlink to reside
        @type symlink_dir str

        @param progress_callback: callback to report progress info to publish_conduit
        @type  progress_callback: function

        @return tuple of status and list of error messages if any occurred
        @rtype (bool, [str])
        """
        distro_progress_status = self.init_progress()
        self.set_progress("distribution", distro_progress_status, progress_callback)
        _LOG.info("Process symlinking distribution files with %s units to %s dir" % (len(units), symlink_dir))
        errors = []
        for u in units:
            source_path_dir  = u.storage_path
            if not u.metadata.has_key('files'):
                msg = "No distribution files found for unit %s" % u
                _LOG.error(msg)
            distro_files =  u.metadata['files']
            _LOG.info("Found %s distribution files to symlink" % len(distro_files))
            distro_progress_status['items_total'] = len(distro_files)
            distro_progress_status['items_left'] = len(distro_files)
            for dfile in distro_files:
                self.set_progress("distribution", distro_progress_status, progress_callback)
                source_path = os.path.join(source_path_dir, dfile['relativepath'])
                symlink_path = os.path.join(symlink_dir, dfile['relativepath'])
                if not os.path.exists(source_path):
                    msg = "Source path: %s is missing" % source_path
                    errors.append((source_path, symlink_path, msg))
                    distro_progress_status['num_error'] += 1
                    distro_progress_status["items_left"] -= 1
                    continue
                try:
                    if not self.create_symlink(source_path, symlink_path):
                        msg = "Unable to create symlink for: %s pointing to %s" % (symlink_path, source_path)
                        _LOG.error(msg)
                        errors.append((source_path, symlink_path, msg))
                        distro_progress_status['num_error'] += 1
                        distro_progress_status["items_left"] -= 1
                        continue
                    distro_progress_status['num_success'] += 1
                except Exception, e:
                    tb_info = traceback.format_exc()
                    _LOG.error("%s" % tb_info)
                    _LOG.critical(e)
                    errors.append((source_path, symlink_path, str(e)))
                    distro_progress_status['num_error'] += 1
                    distro_progress_status["items_left"] -= 1
                    continue
                distro_progress_status["items_left"] -= 1
        if errors:
            distro_progress_status["error_details"] = errors
            distro_progress_status["state"] = "FAILED"
            self.set_progress("distribution", distro_progress_status, progress_callback)
            return False, errors
        distro_progress_status["state"] = "FINISHED"
        self.set_progress("distribution", distro_progress_status, progress_callback)
        return True, []

    def create_consumer_payload(self, repo, config):
        payload = {}
        ##TODO for jdob: load the pulp.conf and make it accessible to distributor
        pulp_conf = load_config(config_file="/etc/pulp/pulp.conf")
        payload['server_name'] = pulp_conf.get('server', 'server_name')
        ssl_ca_path = pulp_conf.get('security', 'ssl_ca_certificate')
        if os.path.exists(ssl_ca_path):
            payload['ca_cert'] = open(pulp_conf.get('security', 'ssl_ca_certificate')).read()
        else:
            payload['ca_cert'] = config.get('https_ca')
        payload['relative_path'] = pulp_conf.get('server', 'relative_url') + self.get_repo_relative_path(repo, config)
        payload['protocols'] = []
        if config.get('http'):
            payload['protocols'].append('http')
        if config.get('https'):
            payload['protocols'].append('https')
        payload['gpg_keys'] = []
        if config.get('gpgkey') is not None:
            payload['gpg_keys'] = config.get('gpgkey')
        payload['client_cert'] = None
        if config.get('auth_cert') and config.get('auth_ca'):
            payload['client_cert'] = config.get('auth_cert')
        else:
            # load the global auth if enabled
            repo_auth_config = load_config()
            global_cert_dir =  repo_auth_config.get('repos', 'global_cert_location')
            global_auth_cert = os.path.join(global_cert_dir, 'pulp-global-repo.cert')
            global_auth_key = os.path.join(global_cert_dir, 'pulp-global-repo.key')
            global_auth_ca = os.path.join(global_cert_dir, 'pulp-global-repo.ca')
            if os.path.exists(global_auth_ca) and os.path.exists(global_auth_cert):
                payload['global_auth_cert'] = open(global_auth_cert).read()
                payload['global_auth_key'] = open(global_auth_key).read()
                payload['global_auth_ca'] = open(global_auth_ca).read()
        return payload

def load_config(config_file=CONFIG_REPO_AUTH):
    config = SafeConfigParser()
    config.read(config_file)
    return config