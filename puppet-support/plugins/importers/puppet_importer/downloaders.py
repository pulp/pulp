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
import shutil

from pulp_puppet.common import constants

# -- constants ----------------------------------------------------------------

METADATA_FILENAME = 'modules.json'

# -- exceptions ---------------------------------------------------------------

class MetadataNotFound(Exception):

    def __init__(self, location):
        Exception.__init__(self, location)
        self.location = location


class ModuleNotFound(Exception):

    def __init__(self, location):
        Exception.__init__(self, location)
        self.location = location

# -- downloader implementations -----------------------------------------------

class LocalDownloader(object):
    """
    Used when the source for puppet modules is a directory local to the Pulp
    server.
    """

    def retrieve_metadata(self, config):
        """
        See module-level docstrings for description.
        """

        source_dir = config.get(constants.CONFIG_SOURCE_DIR)
        metadata_filename = os.path.join(source_dir, METADATA_FILENAME)

        if not os.path.exists(metadata_filename):
            raise MetadataNotFound(metadata_filename)

        f = open(metadata_filename, 'r')
        contents = f.read()
        f.close()

        return contents

    def retrieve_module(self, config, module, destination):
        """
        See module-level docstrings for description.
        """

        # Determine the full path to the module
        source_dir = config.get(constants.CONFIG_SOURCE_DIR)
        module_path = constants.HOSTED_MODULE_FILE_RELATIVE_PATH % (module.author[0], module.author)
        module_filename = module.filename()
        full_filename = os.path.join(source_dir, module_path, module_filename)

        if not os.path.exists(full_filename):
            raise ModuleNotFound(full_filename)

        # Copy into the final destination as provided by Pulp
        shutil.copy(full_filename, destination)


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


class GitDownloader(object):
    """
    Used when the source for puppet modules is a git repository.
    """

    # To be implemented when support for this is required
    pass