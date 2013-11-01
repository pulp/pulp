# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.server.compat import json

from pulp_node import manifest as _manifest


# --- constants --------------------------------------------------------------


PATH = 'path'
VERSION = 'version'
UNITS = 'units'
TOTAL_UNITS = 'total_units'
UNITS_SIZE = 'units_size'
UNITS_PATH = 'units_path'


# --- migrations -------------------------------------------------------------


def migration_0(manifest):
    """
    Migrate v0 -> v1.
    This migration is used to migrate any manifest published prior
    to the introduction of manifest migration capabilities.  In this
    migration, the 'units_path' is set to None because in 2.3.0+, this
    property references an unzipped file.  But, in 2.2, this property
    references the zipped file.
    Manifests with version=None were published by 2.2.
    :param manifest: The migration to migrate.
    :type manifest: dict
    :return: The migrated manifest.
    """
    manifest[VERSION] = 0
    manifest[UNITS_PATH] = None
    return manifest


def migration_1(manifest):
    """
    Migrate v1 -> v2.
    This migration groups unit properties under a 'units' property.
    Manifests with version=1 were published by 2.3.0.
    :param manifest: The migration to migrate.
    :type manifest: dict
    :return: The migrated manifest.
    """
    manifest[UNITS] = {
        _manifest.UNITS_PATH: manifest.get(PATH),
        _manifest.UNITS_TOTAL: manifest.get(TOTAL_UNITS, 0),
        _manifest.UNITS_SIZE: manifest.get(UNITS_SIZE, 0)
    }
    manifest.pop(TOTAL_UNITS)
    manifest.pop(UNITS_SIZE)
    return manifest


MIGRATIONS = {
    0: migration_0,
    1: migration_1,
}


# --- migration API ----------------------------------------------------------

def migrate(path):
    """
    Migrate to latest version.
    :param path: The path to a stored manifest.
    :type: path: str
    """
    with open(path) as fp:
        manifest = json.load(fp)
    version_in = manifest.get(VERSION, 0)
    for version in range(version_in, _manifest.MANIFEST_VERSION):
        migration = MIGRATIONS[version]
        manifest = migration(manifest)
        manifest[VERSION] = version + 1
    if version_in < manifest[VERSION]:
        with open(path, 'w+') as fp:
            json.dump(manifest, fp)
