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
import os
import sys
import time
from gettext import gettext as _

from pulp.client import constants
from pulp.client import utils
from pulp.client.connection import setup_connection, RepoConnection, \
    RestlibException
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit
from pulp.client.json_utils import parse_date

# repo command errors ---------------------------------------------------------

class FileError(Exception):
    pass

class SyncError(Exception):
    pass

# base repo action class ------------------------------------------------------

class RepoAction(Action):

    def setup_connections(self):
        self.pconn = setup_connection(RepoConnection)

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("repository id (required)"))

# repo actions ----------------------------------------------------------------

class List(RepoAction):

    description = _('list available repositories')

    def setup_parser(self):
        self.parser.add_option("--groupid", action="append", dest="groupid",
                               help=_("filter repositories by group id"))

    def run(self):
        if self.opts.groupid:
            repos = self.pconn.repositories_by_groupid(groups=self.opts.groupid)
        else:
            repos = self.pconn.repositories()
        if not len(repos):
            system_exit(os.EX_OK, _("No repositories available to list"))
        print_header(_('List of Available Repositories'))
        for repo in repos:
            print constants.AVAILABLE_REPOS_LIST % (
                    repo["id"], repo["name"], repo["source"], repo["arch"],
                    repo["sync_schedule"], repo['package_count'],
                    repo['files_count'])


class Status(RepoAction):

    description = _('show the status of a repository')

    def run(self):
        id = self.get_required_option('id')
        repo = self.pconn.repository(id)
        syncs = self.pconn.sync_list(id)
        print_header(_('Status for %s') % id)
        print _('Repository: %s') % repo['id']
        print _('Number of Packages: %d') % repo['package_count']
        last_sync = repo['last_sync']
        if last_sync is None:
            last_sync = 'never'
        else:
            last_sync = str(parse_date(last_sync))
        print _('Last Sync: %s') % last_sync
        if not syncs or syncs[0]['state'] not in ('waiting', 'running'):
            return
        print _('Currently syncing:'),
        if syncs[0]['progress'] is None:
            print _('progress unknown')
        else:
            pkgs_left = syncs[0]['progress']['items_left']
            pkgs_total = syncs[0]['progress']['items_total']
            bytes_left = float(syncs[0]['progress']['size_left'])
            bytes_total = float(syncs[0]['progress']['size_total'])
            percent = (bytes_total - bytes_left) / bytes_total
            print _('%d%% done (%d of %d packages downloaded)') % \
                    (int(percent), (pkgs_total - pkgs_left), pkgs_total)


class Content(RepoAction):

    description = _('list the contents of a repository')

    def run(self):
        id = self.get_required_option('id')
        repo = self.pconn.repository(id)
        files = repo['files']
        packages = self.pconn.packages(id)
        print_header(_('Contents of %s') % id)
        print _('files in %s:') % id
        if not files:
            print _(' none')
        else:
            for f in sorted(repo['files']):
                print ' ' + f
        print _('packages in %s:') % id
        if not packages:
            print _(' none')
        else:
            for p in sorted(packages, key=lambda p: p['filename']):
                print ' ' + p['filename']


class Create(RepoAction):

    description = _('create a repository')

    def setup_parser(self):
        super(Create, self).setup_parser()
        self.parser.add_option("--name", dest="name",
                               help=_("common repository name"))
        self.parser.add_option("--arch", dest="arch",
                               help=_("package arch the repository should support"))
        self.parser.add_option("--feed", dest="feed",
                               help=_("url feed to populate the repository"))
        self.parser.add_option("--cacert", dest="cacert",
                               help=_("path location to ca certificate"))
        self.parser.add_option("--cert", dest="cert",
                               help=_("path location to entitlement certificate"))
        self.parser.add_option("--key", dest="key",
                               help=_("path location to entitlement certificate key"))
        self.parser.add_option("--schedule", dest="schedule",
                               help=_("schedule for automatically synchronizing the repository"))
        self.parser.add_option("--symlinks", action="store_true", dest="symlinks",
                               help=_("use symlinks instead of copying bits locally; applicable for local syncs"))
        self.parser.add_option("--relativepath", dest="relativepath",
                               help=_("relative path where the repository is stored and exposed to clients; this defaults to feed path if not specified"))
        self.parser.add_option("--groupid", action="append", dest="groupid",
                               help=_("a group to which the repository belongs; this is just a string identifier"))
        self.parser.add_option("--keys", dest="keys",
                               help=_("a ',' separated list of directories and/or files contining GPG keys"))

    def _get_cert_options(self):
        cacert = self.opts.cacert
        cert = self.opts.cert
        key = self.opts.key
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
        keylist = self.opts.keys
        if keylist:
            reader = KeyReader()
            keylist = reader.expand(keylist)
        repo = self.pconn.create(id, name, arch, feed, symlinks, schedule,
                                 cert_data=cert_data,
                                 relative_path=relative_path,
                                 groupid=groupid,
                                 gpgkeys=keylist)
        print _("Successfully created repository [ %s ]") % repo['id']


class Delete(RepoAction):

    description = _('delete a repository')

    def run(self):
        id = self.get_required_option('id')
        self.pconn.delete(id=id)
        print _("Successful deleted repository [ %s ]") % id


class Update(RepoAction):

    description = _('update a repository')

    # special options that are handled by the
    # specified methods.
    # format (option, method)
    OPTIONS = (
        ('feed', 'updatefeed'),
        ('addkeys', 'addkeys'),
        ('rmkeys', 'rmkeys'),
    )

    def setup_parser(self):
        super(Update, self).setup_parser()
        self.parser.add_option("--name", dest="name",
                               help=_("common repository name"))
        self.parser.add_option("--arch", dest="arch",
                               help=_("package arch the repository should support"))
        self.parser.add_option("--feed", dest="feed",
                               help=_("url feed to populate the repository"))
        self.parser.add_option("--cacert", dest="cacert",
                               help=_("path location to ca certificate"))
        self.parser.add_option("--cert", dest="cert",
                               help=_("path location to entitlement certificate key"))
        self.parser.add_option("--schedule", dest="schedule",
                               help=_("schedule for automatically synchronizing the repository"))
        self.parser.add_option("--symlinks", action="store_true", dest="symlinks",
                               help=_("use symlinks instead of copying bits locally; applicable for local syncs"))
        self.parser.add_option("--relativepath", dest="relativepath",
                               help=_("relative path where the repository is stored and exposed to clients; this defaults to feed path if not specified"))
        self.parser.add_option("--groupid", dest="groupid",
                               help=_("a group to which the repository belongs; this is just a string identifier"))
        self.parser.add_option("--addkeys", dest="addkeys",
                               help=_("a ',' separated list of directories and/or files contining GPG keys"))
        self.parser.add_option("--rmkeys", dest="rmkeys",
                               help=_("a ',' separated list of GPG key names"))
    def run(self):
        id = self.get_required_option('id')
        repo = self.pconn.repository(id)
        if not repo:
            system_exit(os.EX_DATAERR, _("Repository with id: [%s] not found") % id)
        optdict = vars(self.opts)
        for k, v in optdict.items():
            if not v:
                continue
            method = self.find(k)
            if method: # special method
                stale = method(repo, v)
                if stale:
                    repo = self.pconn.repository(id)
                continue
            if k in repo:
                repo[k] = v
        self.pconn.update(repo)
        print _("Successfully updated repository [ %s ]") % repo['id']

    def find(self, option):
        """ find option specification """
        for opt, fn in self.OPTIONS:
            if opt == option:
                return getattr(self, fn)

    def updatefeed(self, repo, feed):
        """ update the feed """
        repo['feed'] = feed

    def addkeys(self, repo, keylist):
        """ add the GPG keys """
        id = str(repo['id'])
        reader = KeyReader()
        keylist = reader.expand(keylist)
        self.pconn.addkeys(id, keylist)

    def rmkeys(self, repo, keylist):
        """ add the GPG keys """
        id = str(repo['id'])
        keylist = keylist.split(',')
        self.pconn.rmkeys(id, keylist)

class Sync(RepoAction):

    description = _('synchronize data to a repository from its feed')

    def setup_parser(self):
        super(Sync, self).setup_parser()
        self.parser.add_option("--timeout", dest="timeout",
                               help=_("synchronization timeout"))
        self.parser.add_option('-F', '--foreground', dest='foreground',
                               action='store_true', default=False,
                               help=_('synchronize repository in the foreground'))

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
        print _('You can safely CTRL+C this current command and it will continue')
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

    def get_task(self):
        id = self.get_required_option('id')
        tasks = self.pconn.sync_list(id)
        if tasks and tasks[0]['state'] in ('waiting', 'running'):
            print _('Sync for repository %s already in progress') % id
            return tasks[0]
        timeout = self.opts.timeout
        task = self.pconn.sync(id, timeout)
        print _('Sync for repository %s started') % id
        return task

    def run(self):
        foreground = self.opts.foreground
        task = self.get_task()
        if not foreground:
            system_exit(os.EX_OK, _('Use "repo status" to check on the progress'))
        self.sync_foreground(task)



class CancelSync(RepoAction):

    description = _('cancel a running sync')

    def run(self):
        id = self.get_required_option('id')
        syncs = self.pconn.sync_list(id)
        if not syncs:
            system_exit(os.EX_OK, _('No sync to cancel'))
        task = syncs[0]
        if task['state'] not in ('waiting', 'running'):
            system_exit(os.EX_OK, _('Sync has completed'))
        taskid = task['id']
        self.pconn.cancel_sync(str(id), str(taskid))
        print _("Sync for repository %s canceled") % id


class Upload(RepoAction):

    description = _('upload package(s) to a repository')

    def setup_parser(self):
        super(Upload, self).setup_parser()
        self.parser.add_option("--dir", dest="dir",
                               help=_("process packages from this directory"))

    def run(self):
        id = self.get_required_option('id')
        files = self.args
        dir = self.opts.dir
        if dir:
            files += utils.processDirectory(dir, "rpm")
        if not files:
            system_exit(os.EX_USAGE,
                        _("Need to provide at least one file to perform upload"))
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
            name, version, release, epoch, arch = pkginfo['nvrea']

            if self.pconn.find_package_by_nvrea(id, name, version, release, epoch, arch):
                system_exit(os.EX_OK, \
                            _("Package [%s] already exists on the server in repo %s") % (pkginfo['pkgname'], id))
 
            pkgstream = base64.b64encode(open(frpm).read())
            status = self.pconn.upload(id, pkginfo, pkgstream)
            if status:
                print _("Successful uploaded [%s] to repo [ %s ]") % \
                        (pkginfo['pkgname'], id)
            else:
                print _("Failed to upload [%s] to repo [ %s ]") % \
                        (pkginfo['pkgname'], id)


class Schedules(RepoAction):

    description = _('list all repository schedules')

    def setup_parser(self):
        pass

    def run(self):
        print_header(_('Available Repository Schedules'))
        schedules = self.pconn.all_schedules()
        for id in schedules.keys():
            print(constants.REPO_SCHEDULES_LIST % (id, schedules[id]))


class ListKeys(RepoAction):

    description = _('list gpg keys')

    def run(self):
        id = self.get_required_option('id')
        for key in self.pconn.listkeys(id):
            print os.path.basename(key)


class Repo(Command):

    description = _('repository specific actions to pulp server')


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
