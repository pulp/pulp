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
import shutil
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

def extract_metadata(module, filename, temp_dir):
    """
    Pulls the module's metadata file out of the module's tarball and updates the
    module instance with its contents. The module instance itself is updated
    as part of this call. It is up to the caller to delete the temp_dir after
    this executes.

    :param module: module instance to extract metadata for
    :type  module: Module

    :param filename: full path to the module file
    :type  filename: str

    :param temp_dir: location the module's files should be extracted to;
           must exist prior to this call
    :type  temp_dir: str

    :raise InvalidTarball: if the module file cannot be opened
    :raise MissingModuleFile: if the module's metadata file cannot be found
    """

    # Attempt to load from the standard metadata file location. If it's not
    # found, try the brute force approach. If it's still not found, that call
    # will raise the appropriate MissingModuleFile exception.
    try:
        metadata_json = _extract_json(module, filename, temp_dir)
    except MissingModuleFile:
        metadata_json = _extract_non_standard_json(module, filename, temp_dir)

    module.update_from_json(metadata_json)

# -- private ------------------------------------------------------------------

def _extract_json(module, filename, temp_dir):
    """
    Extracts the module's metadata file from the tarball. This call will attempt
    to only extract and read the metadata file itself, cleaning up the
    extracted file at the end.

    :raise InvalidTarball: if the module file cannot be opened
    :raise MissingModuleFile: if the module's metadata file cannot be found
    """

    # Extract the module's metadata file itself
    metadata_file_path = '%s-%s-%s/%s' % (module.author, module.name,
                                          module.version,
                                          constants.MODULE_METADATA_FILENAME)

    try:
        tgz = tarfile.open(name=filename)
    except Exception, e:
        raise InvalidTarball(filename), None, sys.exc_info()[2]

    try:
        tgz.extract(metadata_file_path, path=temp_dir)
        tgz.close()
    except Exception, e:
        tgz.close()
        raise MissingModuleFile(filename), None, sys.exc_info()[2]

    # Read in the contents
    temp_filename = os.path.join(temp_dir, metadata_file_path)
    contents = _read_contents(temp_filename)
    return contents


def _extract_non_standard_json(module, filename, temp_dir):
    """
    Called if the module's metadata file isn't found in the standard location.
    The entire module will be extracted to a temporary location and an attempt
    will be made to find the module file. If it still cannot be found, an
    exception is raised. The temporary location is deleted at the end of this
    call regardless.

    :raise InvalidTarball: if the module file cannot be opened
    :raise MissingModuleFile: if the module's metadata file cannot be found
    """

    extraction_dir = os.path.join(temp_dir, module.author, module.name, module.version)
    os.makedirs(extraction_dir)

    # Extract the entire module
    try:
        tgz = tarfile.open(name=filename)
        tgz.extractall(path=extraction_dir)
        tgz.close()
    except Exception, e:
        raise InvalidTarball(filename), None, sys.exc_info()[2]

    try:
        # Recursively look for the metadata file
        metadata_file_dir = _find_file_in_dir(extraction_dir, constants.MODULE_METADATA_FILENAME)

        if metadata_file_dir is None:
            raise MissingModuleFile(filename)

        metadata_filename = os.path.join(metadata_file_dir, constants.MODULE_METADATA_FILENAME)
        contents = _read_contents(metadata_filename)

        return contents
    finally:
        # Delete the entire extraction directory
        extraction_root = os.path.join(temp_dir, module.author)
        shutil.rmtree(extraction_root)


def _read_contents(filename):
    """
    Simple utility to read in the contents of the given file, making sure to
    properly handle the file object.

    :return: contents of the given file
    """
    try:
        f = open(filename)
        contents = f.read()
        f.close()

        return contents
    finally:
        # Clean up the temporary file
        os.remove(filename)

        
def _find_file_in_dir(dir, filename):
    """
    Recursively checks the directory for the presence of a file with the given
    name.

    :param dir:
    :param filename:
    :return:
    """
    for found in os.listdir(dir):
        file_or_dir = os.path.join(dir, found)
        if os.path.isfile(file_or_dir):
            if found == filename:
                return dir
        else:
            sub_dir = _find_file_in_dir(file_or_dir, filename)

            if sub_dir is not None:
                return os.path.join(dir, sub_dir)
    else:
        return None