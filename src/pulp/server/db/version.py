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


current_data_model_version = 1

_version_db = None


class DataModelVersion(Base):

    def __init__(self, version):
        _id = version
        version = version


def _init_db():
    global _version_db
    if _version_db is not None:
        return
    _version_db = get_object_db('data_model', ['version'])


def get_version_from_db():
    pass


def set_version_in_db(version):
    pass


def check_version():
    pass

# validate on import ----------------------------------------------------------

_init_db()
check_version()
