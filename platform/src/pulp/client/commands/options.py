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
Contains CLI framework option and flag instances for options that are used
across multiple command areas. Examples include specifying a repository ID or
specifying notes on a resource.
"""

from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliOption

# -- option descriptions ------------------------------------------------------

DESC_ID = _('unique identifier; only alphanumeric, -, and _ allowed')
DESC_NAME = _('user-readable display name (may contain i18n characters)')
DESC_DESCRIPTION = _('user-readable description (may contain i18n characters)')
DESC_NOTE = _(
    'adds/updates/deletes notes to programmatically identify the resource; '
    'key-value pairs must be separated by an equal sign (e.g. key=value); multiple notes can '
    'be changed by specifying this option multiple times; notes are deleted by '
    'specifying "" as the value')

# -- common options -----------------------------------------------------------

OPTION_REPO_ID = PulpCliOption('--repo-id', DESC_ID, required=True)
OPTION_NAME = PulpCliOption('--display-name', DESC_NAME, required=False)
OPTION_DESCRIPTION = PulpCliOption('--description', DESC_DESCRIPTION, required=False)
OPTION_NOTES = PulpCliOption('--note', DESC_NOTE, required=False, allow_multiple=True)
