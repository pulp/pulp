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
import re
import shutil

from pulp_rpm.yum_plugin import util
_LOG = util.getLogger(__name__)
_ = gettext.gettext

HTTP_PUBLISH_DIR="/var/lib/pulp/published/http/isos"
HTTPS_PUBLISH_DIR="/var/lib/pulp/published/https/isos"
ISO_NAME_REGEX = re.compile(r'^[_A-Za-z0-9-]+$')


def is_valid_prefix(iso_prefix):
    """
    @return: True if the given iso_prefix is a valid match; False otherwise
    """
    return ISO_NAME_REGEX.match(iso_prefix) is not None


def get_http_publish_iso_dir(config=None):
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


def get_https_publish_iso_dir(config=None):
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


def cleanup_working_dir(working_dir):
    """
    remove exported content from working dirctory
    """
    try:
        shutil.rmtree(working_dir)
        _LOG.debug("Cleaned up working directory %s" % working_dir)
    except (IOError, OSError), e:
        _LOG.error("unable to clean up working directory; Error: %s" % e)


def form_lookup_key(rpm):
    rpm_key = (rpm["name"], rpm["epoch"], rpm["version"], rpm['release'], rpm["arch"], rpm["checksumtype"], rpm["checksum"])
    return rpm_key


def form_unit_key_map(units):
    existing_units = {}
    for u in units:
        key = form_lookup_key(u.unit_key)
        existing_units[key] = u
    return existing_units