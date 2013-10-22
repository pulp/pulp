# -*- coding: utf-8 -*-
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

"""
Contains options and flags common across nodes commands.
"""

from gettext import gettext as _

from pulp.client.commands.options import DESC_ID
from pulp.client.extensions.extensions import PulpCliOption
from pulp.client.validators import id_validator_allow_dots
from pulp.client.parsers import pulp_parse_optional_positive_int


# --- descriptions -----------------------------------------------------------

MAX_BANDWIDTH_DESC = _('maximum bandwidth used per download in bytes/sec')
MAX_CONCURRENCY_DESC = _('maximum number of downloads permitted to run concurrently')


# --- options ----------------------------------------------------------------

NODE_ID_OPTION = PulpCliOption(
    '--node-id', DESC_ID, required=True, validate_func=id_validator_allow_dots)

MAX_BANDWIDTH_OPTION = PulpCliOption(
    '--max-speed', MAX_BANDWIDTH_DESC, required=False, parse_func=pulp_parse_optional_positive_int)

MAX_CONCURRENCY_OPTION = PulpCliOption(
    '--max-downloads', MAX_CONCURRENCY_DESC, required=False,
    parse_func=pulp_parse_optional_positive_int)
