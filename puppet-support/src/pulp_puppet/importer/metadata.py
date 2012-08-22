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
Functionality around parsing the metadata within a packaged module (.tar.gz).
"""

import os
import sys
import tarfile

from pulp_puppet.common import constants

# -- exceptions ---------------------------------------------------------------

class ExtractionException(Exception):
    """
    Root exception of all exceptions that can occur while extracting a module's
    metadata.
    """
    def __init__(self, module_filename):
        Exception.__init__(self, module_filename)
        self.module_filename = module_filename


class MissingModuleFile(ExtractionException):
    """
    Raised if the metadata file cannot be extracted from a module.
    """
    pass


class InvalidTarball(ExtractionException):
    """
    Raised if the tarball cannot be opened.
    """
    pass

# -- public -------------------------------------------------------------------

def extract_metadata(module, module_dir, temp_dir):
    """
    Pulls the module's metadata file out of the module's tarball and updates the
    module instance with its contents. The module instance itself is updated
    as part of this call. It is up to the caller to delete the temp_dir after
    this executes.

    :param module: module instance to extract metadata for
    :type  module: Module

    :param module_dir: directory in which the module is located
    :type  module_dir: str

    :param temp_dir: location the module's files should be extracted to;
           must exist prior to this call
    :type  temp_dir: str
    """

    metadata_json = _extract_json(module, module_dir, temp_dir)
    module.update_from_json(metadata_json)

# -- private ------------------------------------------------------------------

def _extract_json(module, module_dir, temp_dir):

    # Extract the module's metadata file itself
    filename = os.path.join(module_dir, module.filename())
    metadata_file_path = '%s-%s-%s/%s' % (module.author, module.name,
                                          module.version,
                                          constants.MODULE_METADATA_FILENAME)

    try:
        tgz = tarfile.open(name=filename)
    except Exception, e:
        raise InvalidTarball(filename), None, sys.exc_info()[2]

    try:
        tgz.extract(metadata_file_path, path=temp_dir)
    except Exception, e:
        raise MissingModuleFile(filename), None, sys.exc_info()[2]

    # Read in the contents
    temp_filename = os.path.join(temp_dir, metadata_file_path)

    f = open(temp_filename)
    contents = f.read()
    f.close()

    return contents