# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
Defines Pulp additions to the okaara base classes. The subclasses
for the individual components that belong to each UI style
(e.g. commands, screens) can be found in extensions.py as they are meant to be
further subclassed by extensions.
"""

from okaara.cli import Cli
from okaara.prompt import Prompt

# -- classes ------------------------------------------------------------------

class PulpPrompt(Prompt):
    pass

class PulpCli(Cli):
    pass