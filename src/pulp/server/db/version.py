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
import os
import sys

import pymongo

from pulp.server.db.connection import get_object_db
from pulp.server.db.model import Base


# current data model version of the code base
# increment this if you change the data model
VERSION = 1

_log = logging.getLogger('pulp')
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

# data model version api ------------------------------------------------------

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
    assert _version_db is not None
    versions = _version_db.find()
    if not versions:
        return None
    versions.sort({'version': pymongo.DESCENDING}).limit(1)
    return list(versions)[0]


def get_version_in_use():
    """
    Fetch the data model version currently in use in the db.
    @rtype: int
    @return: integer data model version
    """
    assert _version_db is not None
    v = _get_latest_version()
    return v.version


def check_version():
    """
    Check for a version mismatch between the current data model version and the
    data model version in use in the db. If a mismatch is detected, the
    mismatch is logged and the application exits.
    """
    assert _version_db is not None
    v = _get_latest_version()
    if v.version == VERSION:
        return
    _log.critical('data model version mismatch: %d in use, but needs to be %d' %
                  v.version, VERSION)
    _log.critical('pulp exiting: please migrate your database to the latest data model')
    sys.exit(os.EX_DATAERR)


def set_version(version):
    """
    Set the data model version in the database.
    @type version: int
    @param version: data model version
    """
    assert _version_db is not None
    v = DataModelVersion(version)
    _version_db.save(v, safe=True)


def is_validated():
    """
    Check to see if the latest data model version has been validated.
    @rtype: bool
    @return: True if the data model has been validated, False otherwise
    """
    assert _version_db is not None
    v = _get_latest_version()
    return v.validated


def set_validated():
    """
    Flag the latest data model version as validated.
    """
    assert _version_db is not None
    v = _get_latest_version()
    v.validated = True
    _version_db.save(v, safe=True)

# check for version mismatch on import ----------------------------------------

_init_db()
check_version()
