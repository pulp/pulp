#!/usr/bin/python
#
# Pulp Filter management module
#
# Copyright (c) 2010 Red Hat, Inc.

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
#

import os
from gettext import gettext as _

from pulp.client import constants
from pulp.client.api.filter import FilterAPI
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit


# base filter action class ------------------------------------------------------

class FilterAction(Action):

    def __init__(self):
        super(FilterAction, self).__init__()
        self.filter_api = FilterAPI()
        
    def get_filter(self, id):
        filter = self.filter_api.filter(id=id)
        if not filter:
            system_exit(os.EX_DATAERR,
                        _("Filter [ %s ] does not exist") % id)
        return filter

# filter actions ----------------------------------------------------------------

class List(FilterAction):

    description = _('list available filters')
    
    def run(self):
        filters = self.filter_api.filters()
        if not len(filters):
            system_exit(os.EX_OK, _("No filters available to list"))
        print_header(_('Available Filters'))
        for filter in filters:
            print constants.AVAILABLE_FILTERS_LIST % (filter["id"], filter["description"],
                                                    filter["type"], filter["package_list"])


class Info(FilterAction):

    description = _('lookup information for a filter')
    
    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("new filter id to create (required)"))
        
    def run(self):
        id = self.get_required_option('id')
        filter = self.filter_api.filter(id)
        if not filter:
            system_exit(os.EX_DATAERR, _("No filter with give id"))
        else:
            print constants.AVAILABLE_FILTERS_LIST % (filter["id"], filter["description"],
                                                    filter["type"], filter["package_list"])


class Create(FilterAction):

    description = _('create a filter')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("new filter id to create (required)"))
        self.parser.add_option("--type", dest="type",
                               help=_("filter type - blacklist/whitelist (required)"))
        self.parser.add_option("--description", dest="description", default=None,
                               help=_("filter description"))
        self.parser.add_option("-p", "--package", action="append", dest="pnames",
                               help=_("packages to be added to the filter; to specify multiple packages use multiple -p"))

    def run(self):
        id = self.get_required_option('id')
        type = self.get_required_option('type')
        if type not in ["blacklist","whitelist"]:
            self.parser.error(_("Invalid argument for option 'type'; please see --help"))
            system_exit(os.EX_USAGE, _("Invalid argument for option 'type'"))

        description = self.opts.description or id
        pnames = self.opts.pnames or []
       
        filter = self.filter_api.create(id, type, description, pnames)
        print _("Successfully created filter [ %s ]" % filter['id'])


class Delete(FilterAction):

    description = _('delete a filter')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("filter id (required)"))
        self.parser.add_option("--force", action="store_false", dest="force", default=True,
                               help=_("force deletion of filter by removing association with repositories"))


    def run(self):
        id = self.get_required_option('id')
        filter = self.get_filter(id)
        force = getattr(self.opts, 'force', True)
        if force:
            force_value = 'false'
        else:
            force_value = 'true'
        print _("Force value: %s") % force_value
        deleted = self.filter_api.delete(id=id, force=force_value)
        if deleted:
            print _("Successfully deleted Filter [ %s ]") % id
        else:
            print _("Filter [%s] not deleted") % id


class AddPackages(FilterAction):

    description = _('add packages to filter')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("new filter id to create (required)"))
        self.parser.add_option("-p", "--package", action="append", dest="pnames",
                               help=_("packages to be added to the filter; to specify multiple packages use multiple -p"))

    def run(self):
        id = self.get_required_option('id')
        pnames = self.opts.pnames or []
        if not pnames:
            system_exit(os.EX_USAGE, _("At least one package regex needs to be provided"))
        filter = self.filter_api.add_packages(id, pnames)
        print _("Successfully added packages to filter [ %s ]" % id)


class RemovePackages(FilterAction):

    description = _('remove packages from filter')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("new filter id to create (required)"))
        self.parser.add_option("-p", "--package", action="append", dest="pnames",
                               help=_("packages to be removed from the filter; to specify multiple packages use multiple -p"))

    def run(self):
        id = self.get_required_option('id')
        pnames = self.opts.pnames or []
        if not pnames:
            system_exit(os.EX_USAGE, _("At least one package regex needs to be provided"))
        filter = self.filter_api.remove_packages(id, pnames)
        print _("Successfully removed packages to filter [ %s ]" % id)

# filter command ----------------------------------------------------------------

class Filter(Command):

    description = _('filter specific actions to pulp server')
