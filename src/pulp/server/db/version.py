# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import logging

import pymongo

from pulp.server.db.connection import get_object_db
from pulp.server.db.model import Base


# current data model version of the code base
# increment this if you change the data model
VERSION = 2

# this isn't anything
_version_db = None

# data model version model ----------------------------------------------------

class DataModelVersion(Base):
    """
    Simple data model to store data model versions and migrations in the
    database.
    @ivar version: version of the data model
    @ivar validated: boolean flag set to True if the data model has been
                     validated, False initially
    """
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
    _version_db = get_object_db('data_model', ['version'])


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


def is_validated():
    """
    Check to see if the latest data model version has been validated.
    @rtype: bool
    @return: True if the data model has been validated, False otherwise
    """
    v = _get_latest_version()
    return v['validated']


def set_validated():
    """
    Flag the latest data model version as validated.
    """
    v = _get_latest_version()
    if v['validated']:
        return
    v['validated'] = True
    _update_version(v)
