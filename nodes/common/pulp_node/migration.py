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


# --- migrations -------------------------------------------------------------

def migration_1(manifest):
    manifest[UNITS] = {
        _manifest.UNITS_PATH: manifest.get(PATH),
        _manifest.UNITS_TOTAL: manifest.get(TOTAL_UNITS, 0),
        _manifest.UNITS_SIZE: manifest.get(UNITS_SIZE, 0)
    }
    manifest.pop(TOTAL_UNITS)
    manifest.pop(UNITS_SIZE)
    return manifest


MIGRATIONS = {
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
    version_in = manifest[VERSION]
    for version in range(version_in, _manifest.MANIFEST_VERSION):
        migration = MIGRATIONS[version]
        manifest = migration(manifest)
        manifest[VERSION] = version + 1
    if version_in < manifest[VERSION]:
        with open(path, 'w+') as fp:
            json.dump(manifest, fp)
