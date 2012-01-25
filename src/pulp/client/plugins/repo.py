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

from pulp.client.api.repository import RepositoryAPI
from pulp.client.lib.utils import print_header, system_exit
from pulp.client import constants
from pulp.client.lib.logutil import getLogger
from pulp.client.pluginlib.command import Action, Command

log = getLogger(__name__)

# base repo action class ------------------------------------------------------

class RepoAction(Action):

    def __init__(self, cfg):
        super(RepoAction, self).__init__(cfg)
        self.repository_api = RepositoryAPI()

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("repository id (required)"))

    def print_repo(self, repo):
        feedUrl = feedType = None
        if repo['source']:
            feedUrl = repo['source']['url']
            feedType = repo['source']['type']
        filters = []
        for filter in repo['filters']:
            filters.append(filter)

        feed_cert = 'No'
        if repo.has_key('feed_cert') and repo['feed_cert']:
            feed_cert = 'Yes'
        feed_ca = 'No'
        if repo.has_key('feed_ca') and repo['feed_ca']:
            feed_ca = 'Yes'

        consumer_cert = 'No'
        if repo.has_key('consumer_cert') and repo['consumer_cert']:
            consumer_cert = 'Yes'
        consumer_ca = 'No'
        if repo.has_key('consumer_ca') and repo['consumer_ca']:
            consumer_ca = 'Yes'

        repo['files_count'] = len(self.repository_api.list_files(repo['id']))
        print constants.AVAILABLE_REPOS_LIST % (
                repo["id"], repo["name"], repo['uri'], feedUrl, feedType,
                repo["content_types"], feed_ca, feed_cert, consumer_ca,
                consumer_cert, repo["arch"], repo["sync_schedule"],
                repo['package_count'], repo['files_count'],
                ' '.join(repo['distributionid']) or None, repo['publish'],
                repo['clone_ids'], repo['groupid'] or None, filters,
                repo['notes'], repo['preserve_metadata'], repo['checksum_type'])

# repo actions ----------------------------------------------------------------

class List(RepoAction):

    name = "list"
    description = _('list available repositories')

    def setup_parser(self):
        self.parser.add_option("--groupid", dest="groupid",
                               help=_("filter repositories by group id"))
        self.parser.add_option("--note", dest="note",
                               help=_("filter repositories by note; note should be specified in key:value format"))

    def run(self):
        searchdict = {}
        if self.opts.groupid:
            searchdict["groupid"] = self.opts.groupid
        if self.opts.note:
            searchdict["note"] = self.opts.note

        repos = self.repository_api.repositories(queries=searchdict)
        if not len(repos):
            system_exit(os.EX_OK, _("No repositories available to list"))
        print_header(_('List of Available Repositories'))
        for repo in repos:
            self.print_repo(repo)

# repo command ----------------------------------------------------------------

class Repo(Command):

    name = "repo"
    description = _('repository specific actions to pulp server')
