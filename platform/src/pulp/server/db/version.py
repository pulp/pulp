# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging

import pymongo

#from pulp.server.db.connection import get_object_db
from pulp.server.db.model.base import Model


# current data model version of the code base
# increment this if you change the data model
VERSION = 1

# this isn't anything
_version_db = None

# data model version model ----------------------------------------------------

class DataModelVersion(Model):
    """
    Simple data model to store data model versions and migrations in the
    database.
    @ivar version: version of the data model
    @ivar validated: boolean flag set to True if the data model has been
                     validated, False initially
    """

    collection_name = 'data_model'
    unique_indices = ('version',)

    def __init__(self, version):
        """
        @type version: int
        @param version: data model version this model represents
        """
        self._id = version
        self.version = version
        self.validated = False

# database access functions ---------------------------------------------------

def _init_db():
    """
    Initialize the database connection.
    """
    global _version_db
    if _version_db is not None:
        return
    #_version_db = get_object_db('data_model', ['version'])
    _version_db = DataModelVersion.get_collection()

def clean_db():
    """
    Removes the version collection from our database in mongo
    """
    _init_db()
    global _version_db
    if _version_db is not None:
        _version_db.remove(safe=True)
        _version_db = None


def _get_all_versions():
    """
    Utility function to fetch all of the version information from the database.
    @rtype: list of L{DataModelVersion} instances
    @return: (potentially empty) list of all data model instances in the db
    """
    _init_db()
    versions = _version_db.find()
    versions.sort('version', pymongo.ASCENDING)
    return list(versions)


def _get_latest_version():
    """
    Utility function to fetch the latest DataModelVersion model from the db.
    @rtype: L{DataModelVersion} instance
    @return: the data model intance with the most recent version
    """
    _init_db()
    versions = _version_db.find()
    if versions.count() == 0:
        return None
    versions.sort('version', pymongo.DESCENDING).limit(1)
    return list(versions)[0]


def _set_version(version):
    """
    Utility function to save versions to the database.
    @type version: L{DataModelVersion} instance
    @param version: the version to save
    """
    _init_db()
    _version_db.save(version, safe=True)


def _update_version(version):
    """
    Utility function to update versions in the database.
    @type version: L{DataModelVersion} instance
    @param version: the version to update
    """
    _init_db()
    _version_db.update({'_id': version['_id']}, version, safe=True)

def _remove_version(version):
    """
    Utility function to remove a version in the database.
    @type version: L{DataModelVersion} instance
    @param version: the version to update
    """
    _init_db()
    _version_db.remove({'_id': version['_id']}, safe=True)

# data model version api ------------------------------------------------------

def get_version_in_use():
    """
    Fetch the data model version currently in use in the db.
    @rtype: int
    @return: integer data model version
    """
    v = _get_latest_version()
    if v is None:
        return None
    return v['version']


def check_version():
    """
    Check for a version mismatch between the current data model version and the
    data model version in use in the db. If a mismatch is detected, the
    mismatch is logged and the application exits.
    """
    v = _get_latest_version()
    if v is not None and v['version'] == VERSION and v['validated']:
        return
    if v is None or v['version'] != VERSION:
        msg = 'data model version mismatch: %s in use, but needs to be %s' % \
                (v and v['version'], VERSION)
    else:
        msg = 'data model version is up to date, but has not been validated'
    log = logging.getLogger('pulp')
    log.critical(msg)
    log.critical("use the 'pulp-migrate' tool to fix this before restarting the web server")
    raise RuntimeError(msg)


def set_version(version):
    """
    Set the data model version in the database.
    @type version: int
    @param version: data model version
    """
    v = DataModelVersion(version)
    _set_version(v)


def revert_to_version(version):
    """
    Set the data model version in the database to the passed in version,
    removing any subsequent data model version information.
    @type version: int
    @param version: data model version
    """
    for v in _get_all_versions():
        if v['version'] <= version:
            continue
        _remove_version(v)

def is_validated():
    """
    Check to see if the latest data model version has been validated.
    @rtype: bool
    @return: True if the data model has been validated, False otherwise
    """
    v = _get_latest_version()
    return v['version'] == VERSION and v['validated']


def set_validated():
    """
    Flag the latest data model version as validated.
    """
    v = _get_latest_version()
    if v['validated']:
        return
    v['validated'] = True
    _update_version(v)
