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

from pulp.server.db.connection import get_object_db
from pulp.server.db.model import Base


VERSION = 1

_version_db = None


class DataModelVersion(Base):

    def __init__(self, version):
        self._id = version
        self.version = version
        self.is_validated = False


def _init_db():
    global _version_db
    if _version_db is not None:
        return
    _version_db = get_object_db('data_model', ['version'])


def get_version_in_use():
    pass


def set_version(version):
    pass


def set_validated():
    pass


def check_version():
    pass

# validate on import ----------------------------------------------------------

_init_db()
check_version()
