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

from gettext import gettext as _

from pulp.client.commands.repo.sync_publish import StatusRenderer


# --- constants -----------------------------------------------------------------------------------

RESOURCE_TYPES = {
    'consumer': _('Consumer'),
    'repository': _('Repository')
}

MISSING_RESOURCE = _('%(type)s [%(id)s] not found')


# --- functions -----------------------------------------------------------------------------------


def missing_resources(exception):
    s = []
    for _type, _id in exception.extra_data['resources'].items():
        _type = RESOURCE_TYPES.get(_type, _type)
        s.append(MISSING_RESOURCE % {'type': _type, 'id': _id})
    return '\n'.join(s)


# --- classes -------------------------------------------------------------------------------------


class PublishRenderer(StatusRenderer):

    def __init__(self, context):
        super(PublishRenderer, self).__init__(context)

    def display_report(self, progress_report):
        pass # nothing to report