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
from gettext import gettext as _, gettext
from pulp.client.commands.criteria import UnitAssociationCriteriaCommand

class UnitCopyCommand(UnitAssociationCriteriaCommand):
    def __init__(self, method, *args, **kwargs):
        kwargs['include_search'] = False
        super(UnitCopyCommand, self).__init__(method, *args, **kwargs)
        self.options = [opt for opt in self.options if opt.name != '--repo-id']

        m = 'source repository from which units will be copied'
        self.create_option('--from-repo-id', _(m), ['-f'], required=True)

        m = 'destination repository to copy units into'
        self.create_option('--to-repo-id', _(m), ['-t'], required=True)


class UnitRemoveCommand(UnitAssociationCriteriaCommand):
    def __init__(self, *args, **kwargs):
        kwargs['include_search'] = False
        super(UnitRemoveCommand, self).__init__(*args, **kwargs)