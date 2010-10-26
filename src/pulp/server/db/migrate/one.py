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


# This is an example migration module. Each version of the database should
# provide a module that contains the code necessary to migrate the database to
# that version. We leave the developer to decide how best to implement this
# module. There is no set conventions. This module will be imported into and
# used directly by the script module.

import logging

from pulp.server.db import version


_log = logging.getLogger('pulp')


def migrate():
    # There's a bit of the chicken and the egg problem here, since versioning
    # wasn't built into pulp from the beginning, we just have to bite the
    # bullet and call some initial state of the data model 'version 1'.
    # So this function is essentially a no-op.
    _log.info('migration to data model version 1 starting')
    _log.info('migration to data model version 1 complete')


def set_version():
    version.set_version(1)
