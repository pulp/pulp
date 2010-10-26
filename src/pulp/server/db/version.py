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

import pymongo

from pulp.server.db.connection import get_object_db
from pulp.server.db.model import Base


VERSION = 1

_version_db = None


class DataModelVersion(Base):

    def __init__(self, version):
        self._id = version
        self.version = version
        self.validated = False


def _init_db():
    global _version_db
    if _version_db is not None:
        return
    _version_db = get_object_db('data_model', ['version'])


def _get_latest_version():
    assert _version_db is not None
    versions = _version_db.find()
    if not versions:
        return None
    versions.sort({'version': pymongo.DESCENDING}).limit(1)
    return list(versions)[0]


def get_version_in_use():
    assert _version_db is not None
    v = _get_latest_version()
    return v.version


def check_version():
    assert _version_db is not None
    v = _get_latest_version()
    # XXX this should log and exit if there is a version mismatch,
    # not return a boolean
    return v.version == VERSION


def set_version(version):
    assert _version_db is not None
    v = DataModelVersion(version)
    _version_db.save(v, safe=True)


def is_validated():
    assert _version_db is not None
    v = _get_latest_version()
    return v.validated


def set_validated():
    assert _version_db is not None
    v = _get_latest_version()
    v.validated = True
    _version_db.save(v, safe=True)

# validate on import ----------------------------------------------------------

_init_db()
check_version()
