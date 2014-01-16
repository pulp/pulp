# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from collections import namedtuple
from gettext import gettext as _

Error = namedtuple('Error', ['code', 'message', 'required_fields'])
"""
The error named tuple has 4 components:
code: The 7 character uniquely identifying code for this error, 3 A-Z identifying the module
      followed by 4 numeric characters for the msg id.  All general pulp server errors start
      with PLP
message: The message that will be printed for this error
required_files: A list of required fields for printing the message
"""

# The PLP0000 error is to wrap non-pulp exceptions
PLP0000 = Error("PLP0000",
                "%(message)s", ['message'])
PLP0001 = Error("PLP0001",
                _("A general pulp exception occurred"), [])
PLP0002 = Error("PLP0002",
                _("Errors occurred updating bindings on consumers for repo %(repo_id)s and "
                "distributor %(distributor_id)s"), ['repo_id', 'distributor_id'])
PLP0003 = Error("PLP0003",
                _("Errors occurred removing bindings on consumers while deleting a distributor for "
                  "repo %(repo_id)s and distributor %(distributor_id)s"),
                ['repo_id', 'distributor_id'])
PLP0004 = Error("PLP0004",
                _("Errors occurred creating bindings for the repository group %(group_id)s.  "
                  "Binding creation was attempted for the repository %(repo_id)s and "
                  "distributor %(distributor_id)s"),
                ['repo_id', 'distributor_id', 'group_id'])

PLP0005 = Error("PLP0005",
                _("Errors occurred deleting bindings for the repository group %(group_id)s.  "
                  "Binding deletion was attempted for the repository %(repo_id)s and "
                  "distributor %(distributor_id)s"),
                ['repo_id', 'distributor_id', 'group_id'])
PLP0006 = Error("PLP0006", _("Errors occurred while updating the distributor configuration for "
                             "repository %(repo_id)s"),
                ['repo_id'])
PLP0007 = Error("PLP0007",
                _("Error occurred while cascading delete of repository %(repo_id to distributor"
                  "bindings associated with it."),
                ['repo_id'])
