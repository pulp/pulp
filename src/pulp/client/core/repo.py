#!/usr/bin/python
#
# Pulp Repo management module
#
# Copyright (c) 2010 Red Hat, Inc.
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
#

import base64
import sys
import time
from gettext import gettext as _

from pulp.client import constants
from pulp.client import utils
from pulp.client.connection import RepoConnection
from pulp.client.core.base import Action, print_header, BaseCore, system_exit

# repo command errors ---------------------------------------------------------

class FileError(Exception):
    pass

class SyncError(Exception):
    pass

# base repo action class ------------------------------------------------------

class RepoAction(Action):

    def connections(self):
        return {'pconn': RepoConnection}

    def setup_parser(self):
        self.parser.add_option("--id", dest="id", help="repository id")

# repo actions ----------------------------------------------------------------

class List(RepoAction):

    name = 'list'
    description = 'list available repos'

    def setup_parser(self):
        self.parser.add_option("--groupid", action="append", dest="groupid",
                               help="filter repositories by group id")

    def run(self):
        if self.opts.groupid:
            repos = self.pconn.repositories_by_groupid(groups=self.opts.groupid)
        else:
            repos = self.pconn.repositories()
        if not len(repos):
            print _("no repos available to list")
            sys.exit(0)
        print_header('List of Available Repositories')
        for repo in repos:
            print constants.AVAILABLE_REPOS_LIST % (
                    repo["id"], repo["name"], repo["source"], repo["arch"],
                    repo["sync_schedule"], repo['package_count'],
                    repo['files_count'])


class Status(RepoAction):

    name = 'status'
    description = 'show the status of a repo'

    def run(self):
        id = self.get_required_option('id')
        repo = self.pconn.repository(id)
        syncs = self.pconn.sync_list(id)
        print _('Repository: %s') % repo['id']
        print _('Number of Packages: %d') % repo['package_count']
        last_sync = 'never' if repo['last_sync'] is None else str(repo['last_sync'])
        print _('Last Sync: %s') % last_sync
        if syncs and syncs[0]['state'] in ('waiting', 'running'):
            print _('Currently Syncing:'),
            if syncs[0]['progress'] is None:
                print _('starting')
            else:
                pkgs_left = syncs[0]['progress']['items_left']
                pkgs_total = syncs[0]['progress']['items_total']
                bytes_left = float(syncs[0]['progress']['size_left'])
                bytes_total = float(syncs[0]['progress']['size_total'])
                percent = (bytes_total - bytes_left) / bytes_total
                print _('%d%% done (%d of %d packages downloaded)') % \
                        (int(percent), (pkgs_total - pkgs_left), pkgs_total)


class Create(RepoAction):

    name = 'create'
    description = 'create a repo'

    def setup_parser(self):
        super(Create, self).setup_parser()
        self.parser.add_option("--name", dest="name",
                               help="common repository name")
        self.parser.add_option("--arch", dest="arch",
                               help="package arch the repository should support")
        self.parser.add_option("--feed", dest="feed",
                               help="url feed to populate the repository")
        self.parser.add_option("--cacert", dest="cacert",
                               help="path location to ca certificate")
        self.parser.add_option("--cert", dest="cert",
                               help="path location to entitlement certificate key")
        self.parser.add_option("--schedule", dest="schedule",
                               help="schedule for automatically synchronizing the repository")
        self.parser.add_option("--symlinks", action="store_true", dest="symlinks",
                               help="use symlinks instead of copying bits locally; applicable for local syncs")
        self.parser.add_option("--relativepath", dest="relativepath",
                               help="relative path where the repository is stored and exposed to clients; this defaults to feed path if not specified")
        self.parser.add_option("--groupid", dest="groupid",
                               help="a group to which the repository belongs; this is just a string identifier")

    def _get_cert_options(self):
        cacert = self.opts.cacert
        cert = self.opts.cert
        # XXX this looks like a bug from the original code
        key = getattr(self.opts, 'key', None)
        if not (cacert and cert and key):
            return None
        return {"ca": utils.readFile(cacert),
                "cert": utils.readFile(cert),
                "key": utils.readFile(key)}

    def run(self):
        id = self.get_required_option('id')
        name = self.opts.name or id
        arch = self.opts.arch or 'noarch'
        feed = self.opts.feed
        symlinks = self.opts.symlinks or False
        schedule = self.opts.schedule
        relative_path = self.opts.relativepath
        groupid = self.opts.groupid
        cert_data = self._get_cert_options()
        repo = self.pconn.create(id, name, arch, feed, symlinks, schedule,
                                 cert_data=cert_data,
                                 relative_path=relative_path, groupid=groupid)
        print _(" successfully created repo [ %s ]") % repo['id']


class Delete(RepoAction):

    name = 'delete'
    description = 'delete a repo'

    def run(self):
        id = self.get_required_option('id')
        self.pconn.delete(id=id)
        print _(" successful deleted repo [ %s ]") % id


class Update(RepoAction):

    name = 'update'
    description = 'update a repo'

    def setup_parser(self):
        super(Update, self).setup_parser()
        self.parser.add_option("--name", dest="name",
                               help="common repository name")
        self.parser.add_option("--arch", dest="arch",
                               help="package arch the repository should support")
        self.parser.add_option("--feed", dest="feed",
                               help="url feed to populate the repository")
        self.parser.add_option("--cacert", dest="cacert",
                               help="path location to ca certificate")
        self.parser.add_option("--cert", dest="cert",
                               help="path location to entitlement certificate key")
        self.parser.add_option("--schedule", dest="schedule",
                               help="schedule for automatically synchronizing the repository")
        self.parser.add_option("--symlinks", action="store_true", dest="symlinks",
                               help="use symlinks instead of copying bits locally; applicable for local syncs")
        self.parser.add_option("--relativepath", dest="relativepath",
                               help="relative path where the repository is stored and exposed to clients; this defaults to feed path if not specified")
        self.parser.add_option("--groupid", dest="groupid",
                               help="a group to which the repository belongs; this is just a string identifier")

    def run(self):
        id = self.get_required_option('id')
        repo = self.pconn.repository(id)
        if not repo:
            system_exit(1, _("repo with id: [%s] not found") % id)
        optdict = vars(self.opts)
        for field in optdict.keys():
            if (repo.has_key(field) and optdict[field]):
                repo[field] = optdict[field]
        # Have to set this manually since the repo['feed'] is a 
        # complex sub-object inside the repo
        if self.opts.feed:
            repo['feed'] = self.opts.feed
        self.pconn.update(repo)
        print _(" successfully updated repo [ %s ]") % repo['id']


class Sync(RepoAction):

    name = 'sync'
    description = 'sync data to this repo from the feed'

    def setup_parser(self):
        super(Sync, self).setup_parser()
        self.parser.add_option("--timeout", dest="timeout",
                               help="synchronization timeout")
        self.parser.add_option('-F', '--foreground', dest='foreground',
                               action='store_true', default=False,
                               help='synchronize repository in the foreground')

    def print_sync_progress(self, progress):
        # erase the previous progress
        if hasattr(self, '_previous_progress'):
            sys.stdout.write('\b' * (len(self._previous_progress)))
            sys.stdout.flush()
            delattr(self, '_previous_progress')
        # handle the initial None case
        if progress is None:
            self._previous_progress = '[' + ' ' * 53 + '] 0%'
            sys.stdout.write(self._previous_progress)
            sys.stdout.flush()
            return
        # calculate the progress
        done = float(progress['size_total']) - float(progress['size_left'])
        total = float(progress['size_total'])
        portion = done / total
        percent = str(int(100 * portion))
        pkgs_done = str(progress['items_total'] - progress['items_left'])
        pkgs_total = str(progress['items_total'])
        # create the progress bar
        bar_width = 50
        bar_ticks = '=' * int(bar_width * portion)
        bar_spaces = ' ' * (bar_width - len(bar_ticks))
        bar = '[' + bar_ticks + bar_spaces + ']'
        # set the previous progress and print
        self._previous_progress = '%s %s%% (%s of %s pkgs)' % \
            (bar, percent, pkgs_done, pkgs_total)
        sys.stdout.write(self._previous_progress)
        sys.stdout.flush()

    def print_sync_finish(self, state, progress):
        self.print_sync_progress(progress)
        print ''
        print _('Sync: %s') % state.title()

    def sync_foreground(self, task):
        print _('you can safely CTRL+C this current command and it will continue')
        try:
            while task['state'] not in ('finished', 'error', 'timed out', 'canceled'):
                self.print_sync_progress(task['progress'])
                time.sleep(0.25)
                task = self.pconn.sync_status(task['status_path'])
        except KeyboardInterrupt:
            print ''
            return
        self.print_sync_finish(task['state'], task['progress'])
        if task['state'] == 'error':
            raise SyncError(task['traceback'][-1])

    def run(self):
        id = self.get_required_option('id')
        timeout = self.opts.timeout
        foreground = self.opts.foreground
        task = self.pconn.sync(id, timeout)
        print _('sync for repo %s started') % id
        if not foreground:
            system_exit(0, _('use "repo status" to check on the progress'))
        self.sync_foreground(task)



class CancelSync(RepoAction):

    name = 'cancel_sync'
    description = 'cancel a running sync'

    def setup_parser(self):
        super(CancelSync, self).setup_parser()
        self.parser.add_option("--taskid", dest="taskid", help="task id")

    def run(self):
        id = self.get_required_option('id')
        taskid = self.get_required_option('taskid')
        self.pconn.cancel_sync(id, taskid)
        print _(" sync task %s canceled") % taskid


class Upload(RepoAction):

    name = 'upload'
    description = 'upload package(s) to this repo'

    def setup_parser(self):
        super(Upload, self).setup_parser()
        self.parser.add_option("--dir", dest="dir",
                               help="process packages from this directory")

    def run(self):
        id = self.get_required_option('id')
        files = self.args
        if not files:
            system_exit(0, _("need to provide at least one file to perform upload"))
        dir = self.opts.dir
        if dir:
            files += utils.processDirectory(dir, "rpm")
        uploadinfo = {}
        uploadinfo['repo'] = id
        for frpm in files:
            try:
                pkginfo = utils.processRPM(frpm)
            except FileError, e:
                print >> sys.stderr, _('error: %s') % e
                continue
            if not pkginfo.has_key('nvrea'):
                print _("Package %s is not an rpm; skipping") % frpm
                continue
            pkgstream = base64.b64encode(open(frpm).read())
            status = self.pconn.upload(id, pkginfo, pkgstream)
            if status:
                print _(" successful uploaded [%s] to repo [ %s ]") % \
                        (pkginfo['pkgname'], id)
            else:
                print _(" failed to upload [%s] to repo [ %s ]") % \
                        (pkginfo['pkgname'], id)


class Schedules(RepoAction):

    name = 'schedules'
    description = 'list all repo schedules'

    def setup_parser(self):
        pass

    def run(self):
        print_header('Available Repository Schedules')
        schedules = self.pconn.all_schedules()
        for id in schedules.keys():
            print(constants.REPO_SCHEDULES_LIST % (id, schedules[id]))

# repo command ----------------------------------------------------------------

class Repo(BaseCore):

    name = 'repo'
    description = _('repository specific actions to pulp server')
    _default_actions = ('list', 'status', 'create', 'delete', 'update',
                        'sync', 'cancel_sync', 'upload', 'schedules')

    def __init__(self, actions=None, action_state={}):
        super(Repo, self).__init__(actions, action_state)
        self.list = List()
        self.status = Status()
        self.create = Create()
        self.delete = Delete()
        self.update = Update()
        self.sync = Sync()
        self.cancel_sync = CancelSync()
        self.upload = Upload()
        self.schedules = Schedules()


command_class = Repo
