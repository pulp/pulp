# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import sys
from pulp.server.db.model import Repo
_log = logging.getLogger('pulp')

version = 25

DUPLICATE_WARNING_MSG = """WARNING: Your database has multiple repos with the same relative path.
This is a deprecated functionality and will not be supported in upcoming versions of pulp.
Please remove the following set(s) of repoids from your pulp server %s\n\n"""

#NOTE: This functionality has been deprecated; no further warning required

def _warning_repo_relativepath():
    pass

def migrate():
    # this is only a db content validation rather migration; no change to db model itself
    _log.info('validation on previous data model version started')
    _warning_repo_relativepath()
    _log.info('validation complete; data model at version %d' % version)
