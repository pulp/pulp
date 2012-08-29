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

"""
Determines the correct downloader implementation to return based on the
feed type.
"""

import logging
import urlparse

from exceptions import UnsupportedFeedType, InvalidFeed
from web import HttpDownloader
from local import LocalDownloader

# -- constants ----------------------------------------------------------------

# Mapping from feed prefix to downloader class
MAPPINGS = {
    'file'  : LocalDownloader,
    'http'  : HttpDownloader,
}

_LOG = logging.getLogger(__name__)

# -- public -------------------------------------------------------------------

def get_downloader(feed, repo, conduit, config, is_cancelled_call):
    """
    Returns an instance of the correct downloader to use for the given feed.

    :param feed: location from which to sync modules
    :type  feed: str

    :param repo: describes the repository being synchronized
    :type  repo: pulp.plugins.model.Repository

    :param conduit: sync conduit used during the sync process
    :type  conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit

    :param config: configuration of the importer and call
    :type  config: pulp.plugins.config.PluginCallConfiguration

    :param is_cancelled_call: callback into the plugin to check if the sync
           has been cancelled
    :type  is_cancelled_call: func

    :return: downloader instance to use for the given feed

    :raise UnsupportedFeedType: if there is no applicable downloader for the
           given feed
    :raise InvalidFeed: if the feed cannot be parsed to determine the type
    """

    feed_type = _determine_feed_type(feed)

    if feed_type not in MAPPINGS:
        raise UnsupportedFeedType(feed_type)

    downloader = MAPPINGS[feed_type](repo, conduit, config, is_cancelled_call)
    return downloader

def is_valid_feed(feed):
    """
    Returns whether or not the feed is valid.

    :param feed: repository source
    :type  feed: str

    :return: true if the feed is valid; false otherwise
    :rtype:  bool
    """
    try:
        feed_type = _determine_feed_type(feed)
        is_valid = feed_type in MAPPINGS
        return is_valid
    except InvalidFeed:
        return False

# -- private ------------------------------------------------------------------

def _determine_feed_type(feed):
    """
    Returns the type of feed represented by the given feed.

    :param feed: feed being synchronized
    :type  feed: str

    :return: type to use to retrieve the downloader instance
    :rtype:  str

    :raise InvalidFeed: if the feed is invalid and a feed cannot be
           determined
    """
    try:
        proto, netloc, path, params, query, frag = urlparse.urlparse(feed)
        return proto
    except Exception:
        _LOG.exception('Exception parsing feed type for feed <%s>' % feed)
        raise InvalidFeed(feed)
