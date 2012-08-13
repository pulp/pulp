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

import os
import shutil

from exceptions import MetadataNotFound, ModuleNotFound
from pulp_puppet.common import constants

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
        metadata_filename = os.path.join(source_dir, constants.REPO_METADATA_FILENAME)

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
