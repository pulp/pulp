#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
from gettext import gettext as _
from optparse import OptionGroup

from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.errata import ErrataAPI
from pulp.client.api.file import FileAPI
from pulp.client.api.package import PackageAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.lib.utils import parse_interval_schedule, system_exit
from pulp.client.lib.logutil import getLogger
from pulp.client.pluginlib.command import Action, Command
from pulp.common.dateutils import (
    parse_iso8601_interval, format_iso8601_datetime, format_iso8601_duration)


log = getLogger(__name__)

# repogroup command errors ---------------------------------------------------------

class FileError(Exception):
    pass

class SyncError(Exception):
    pass

class CloneError(Exception):
    pass

# base repogroup action class ------------------------------------------------------

class RepoGroupAction(Action):

    def __init__(self, cfg):
        super(RepoGroupAction, self).__init__(cfg)
        self.consumer_api = ConsumerAPI()
        self.errata_api = ErrataAPI()
        self.package_api = PackageAPI()
        self.service_api = ServiceAPI()
        self.repository_api = RepositoryAPI()
        self.file_api = FileAPI()

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("repository group id (required)"))

    def find_repogroup_update_delta(self, optdict={}):
        feed_cert_bundle = None
        consumer_cert_bundle = None
        delta = {}

        for k, v in optdict.items():
            if not v:
                continue
            if k in ('remove_consumer_cert', 'remove_feed_cert'):
                continue
            if k == 'arch':
                delta['arch'] = v
                continue
            if k == 'addkeys':
                reader = KeyReader()
                keylist = reader.expand(v)
                delta['addkeys'] = keylist
                continue
            if k == 'rmkeys':
                keylist = v.split(',')
                delta['rmkeys'] = keylist
                continue
            if k in ('feed_ca', 'feed_cert', 'feed_key'):
                f = open(v)
                v = f.read()
                f.close()
                feed_cert_bundle = feed_cert_bundle or {}
                feed_cert_bundle[k[5:]] = v
                continue
            if k in ('consumer_ca', 'consumer_cert', 'consumer_key'):
                f = open(v)
                v = f.read()
                f.close()
                consumer_cert_bundle = consumer_cert_bundle or {}
                consumer_cert_bundle[k[9:]] = v
                continue
            if k == 'delete_schedule':
                k = 'sync_schedule'
                v = None
                delta[k] = v

        # Certificate argument sanity check
        if optdict['remove_feed_cert'] and feed_cert_bundle:
            print _('remove_feed_cert cannot be specified while updating feed certificate items')
            return

        if optdict['remove_consumer_cert'] and consumer_cert_bundle:
            print _('remove_consumer_cert cannot be specified while updating consumer certificate items')
            return

        # If removing the cert bundle, set it to None in the delta. If updating any element
        # of the bundle, add it to the delta. Otherwise, no mention in the delta will
        # have no change to the cert bundles.
        if optdict['remove_feed_cert']:
            delta['feed_cert_data'] = {'ca' : None, 'cert' : None, 'key' : None}
        elif feed_cert_bundle:
            delta['feed_cert_data'] = feed_cert_bundle

        if optdict['remove_consumer_cert']:
            delta['consumer_cert_data'] = {'ca' : None, 'cert' : None, 'key' : None}
        elif consumer_cert_bundle:
            delta['consumer_cert_data'] = consumer_cert_bundle
        return delta


# repogroup actions ----------------------------------------------------------------

class Update(RepoGroupAction):

    name = "update"
    description = _('update all repositories in a repository group')

    def setup_parser(self):
        super(Update, self).setup_parser()
        self.parser.add_option("--arch", dest="arch",
                               help=_("package arch repositories should support"))
        self.parser.add_option("--feed_ca", dest="feed_ca",
                               help=_("path location to the feed's ca certificate"))
        self.parser.add_option("--feed_cert", dest="feed_cert",
                               help=_("path location to the feed's entitlement certificate"))
        self.parser.add_option("--feed_key", dest="feed_key",
                               help=_("path location to the feed's entitlement certificate key"))
        self.parser.add_option("--remove_feed_cert", dest="remove_feed_cert", action="store_true",
                               help=_("if specified, the feed certificate information will be removed from group repositories"))
        self.parser.add_option("--consumer_ca", dest="consumer_ca",
                               help=_("path location to the ca certificate used to verify consumer requests"))
        self.parser.add_option("--consumer_cert", dest="consumer_cert",
                               help=_("path location to the entitlement certificate consumers will be provided at bind to grant access to all group repositories"))
        self.parser.add_option("--consumer_key", dest="consumer_key",
                               help=_("path location to the consumer entitlement certificate key"))
        self.parser.add_option("--remove_consumer_cert", dest="remove_consumer_cert", action="store_true",
                               help=_("if specified, the consumer certificate information will be removed from group repositories"))
        self.parser.add_option("--addkeys", dest="addkeys",
                               help=_("a ',' separated list of directories and/or files containing GPG keys"))
        self.parser.add_option("--rmkeys", dest="rmkeys",
                               help=_("a ',' separated list of GPG key names"))

    def run(self):
        id = self.get_required_option('id')
        optdict = vars(self.opts)
        optdict.pop('id')
        # parse all parameters except sync schedule into delta dictionary
        delta = self.find_repogroup_update_delta(optdict)
        grouprepos = self.repository_api.repositories_by_groupid(id)
        if len(grouprepos) == 0:
            system_exit(os.EX_OK, _("There are no repositories belonging to this group"))
        failed_update_repos = {}
        for repo in grouprepos:
            if delta == {}:
                system_exit(os.EX_OK, _('No update parameters provided. Please add one or more parameters to update.'))
            try:
                self.repository_api.update(repo['id'], delta)
            except Exception, e:
                error_code, error_msg, traceback = e
                failed_update_repos[repo['id']] = error_msg

        if failed_update_repos == {}:
            print _("Successfully updated repositories belonging to group[ %s ]") % id
        else:
            print _("Successfully updated repositories belonging to group[ %s ] except for the following repositories: ") % id
            for k, v in failed_update_repos.items():
                print _("\n[ %s ]\n%s" % (k, v))


class KeyReader:

    def expand(self, keylist):
        """ expand the list of directories/files and read content """
        if keylist:
            keylist = keylist.split(',')
        else:
            return []
        try:
            paths = []
            for key in keylist:
                if os.path.isdir(key):
                    for fn in os.listdir(key):
                        paths.append(os.path.join(key, fn))
                    continue
                if os.path.isfile(key):
                    paths.append(key)
                    continue
                raise Exception, _('%s must be file/directory') % key
            keylist = []
            for path in paths:
                print _('uploading %s') % path
                f = open(path)
                fn = os.path.basename(path)
                content = f.read()
                keylist.append((fn, content))
                f.close()
            return keylist
        except Exception, e:
            system_exit(os.EX_DATAERR, _(str(e)))

# repogroup command ----------------------------------------------------------------

class RepoGroup(Command):

    name = "repogroup"
    description = _('repository group specific actions to pulp server')
    actions = [ Update ]

# repogroup plugin ----------------------------------------------------------------

class RepoPlugin(AdminPlugin):

    name = "repogroup"
    commands = [ RepoGroup ]
