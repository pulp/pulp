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
Contains protocol handlers for retrieving puppet modules from various
sources. Each downloader class must implement the following methods:

retrieve_metadata(config)
  Returns the contents of the source's metadata file describing available modules.

retrieve_module(config, module_metadata, destination)
  Copies the specified module bits into the given location. This may involve
  downloading the module from an external source.
"""

import os

import constants

METADATA_FILENAME = 'modules.json'

class MetadataNotFound(Exception):

    def __init__(self, location):
        Exception.__init__(self, location)
        self.location = location


class LocalDownloader(object):
    """
    Used when the source for puppet modules is a directory local to the Pulp
    server.
    """

    def retrieve_metadata(self, config):

        source_dir = config.get(constants.CONFIG_DIR)
        metadata_filename = os.path.join(source_dir, METADATA_FILENAME)

        if not os.path.exists(metadata_filename):
            raise MetadataNotFound(metadata_filename)

        f = open(metadata_filename, 'r')
        contents = f.read()
        f.close()

        return contents

    def retrieve_module(self, config, module_metadata, destination):
        pass

class HttpDownloader(object):
    """
    Used when the source for puppet modules is a remote source over HTTP.
    """

    # To be implemented when support for this is required
    pass

class HttpsDownloader(object):
    """
    Used when the source for puppet modules is a remote source over HTTPS.
    """

    # To be implemented when support for this is required
    pass
