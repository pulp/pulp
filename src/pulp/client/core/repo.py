#!/usr/bin/python
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

import os
import string
import sys
import time
from gettext import gettext as _

from pulp.client import constants
from pulp.client import utils
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.errata import ErrataAPI
from pulp.client.api.package import PackageAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.api.file import FileAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit
from pulp.client.json_utils import parse_date
from pulp.client.logutil import getLogger

log = getLogger(__name__)
# repo command errors ---------------------------------------------------------

class FileError(Exception):
    pass

class SyncError(Exception):
    pass

class CloneError(Exception):
    pass

# base repo action class ------------------------------------------------------

class RepoAction(Action):

    def __init__(self):
        super(RepoAction, self).__init__()
        self.consumer_api = ConsumerAPI()
        self.errata_api = ErrataAPI()
        self.package_api = PackageAPI()
        self.service_api = ServiceAPI()
        self.repository_api = RepositoryAPI()
        self.file_api = FileAPI()

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("repository id (required)"))

    def get_repo(self, id):
        """
        Convenience method for getting a required repository from pulp, and
        exiting with an appropriate error message if the repository doesn't
        exist.
        @type id: str
        @param id: repository id
        @rtype: dict
        @return: dictionary representing the repository
        """
        assert hasattr(self, 'repository_api')
        repo = self.repository_api.repository(id)
        if repo is None:
            system_exit(os.EX_DATAERR, _("Repository with id: [%s] not found") % id)
        return repo


    def handle_dependencies(self, srcrepo, tgtrepo=None, pkgnames=[], recursive=0, assumeyes=False):
        deps = self.service_api.dependencies(pkgnames, [srcrepo], recursive)['available_packages']
        deplist = [{'name'    :   dep['name'],
                    'version' : dep['version'],
                    'release' : dep['release'],
                    'epoch'   : dep['epoch'],
                    'arch'    : dep['arch']} for dep in deps]
        new_deps = []
        if tgtrepo:
            avail_deps = self.repository_api.find_package_by_nvrea(tgtrepo, deplist) or []
            for dep in deps:
                if dep['filename'] not in avail_deps:
                    new_deps.append(dep)
        else:
            new_deps = deps
        if not new_deps:
            # None relevant, return
            print(_("No dependencies to process.."))
            return []
        if not assumeyes:
            do_deps = ''
            while do_deps.lower() not in ['y', 'n', 'q']:
                do_deps = raw_input(_("\nFollowing dependencies are suggested. %s \nWould you like us to add these?(Y/N/Q):" \
                                      % [dep['filename'] for dep in new_deps]))
                if do_deps.strip().lower() == 'y':
                    assumeyes = True
                elif do_deps.strip().lower() == 'n':
                    print(_("Skipping dependencies"))
                    return []
                elif do_deps.strip().lower() == 'q':
                    system_exit(os.EX_OK, _("Operation aborted upon user request."))
                else:
                    continue
        return new_deps

    def lookup_repo_packages(self, filename, repoid, checksum=None, checksum_type="sha256"):
        pkgobj = self.service_api.search_packages(filename=filename,
                                                  checksum=checksum,
                                                  checksum_type=checksum_type)
        for pkg in pkgobj:
            pkg_repos = pkg["repos"]
            if repoid in pkg_repos:
                return pkg
        return None


class RepoProgressAction(RepoAction):

    def __init__(self):
        RepoAction.__init__(self)
        self._previous_progress = None
        self.wait_index = 0
        self.wait_symbols = "|/-\|/-\\"
        self._previous_step = None

    def terminal_size(self):
        import fcntl, termios, struct
        h, w, hp, wp = struct.unpack('HHHH',
            fcntl.ioctl(0, termios.TIOCGWINSZ,
                struct.pack('HHHH', 0, 0, 0, 0)))
        return w, h

    def count_linewraps(self, data):
        linewraps = 0
        width = height = 0
        try:
            width, height = self.terminal_size()
        except:
            # Unable to query terminal for size
            # so default to 0 and skip this 
            # functionality
            return 0
        for line in data.split('\n'):
            count = 0
            for d in line:
                if d in string.printable:
                    count += 1
            linewraps += count / width
        return linewraps

    def write(self, current, prev=None):
        """ Use information of number of columns to guess if the terminal
        will wrap the text, at which point we need to add an extra 'backup line'
        """
        lines = 0
        if prev:
            lines = prev.count('\n')
            if prev.rstrip(' ')[-1] != '\n':
                lines += 1 # Compensate for the newline we inject in this method at end
            lines += self.count_linewraps(prev)
        # Move up 'lines' lines and move cursor to left
        sys.stdout.write('\033[%sF' % (lines))
        sys.stdout.write('\033[J')  # Clear screen cursor down
        sys.stdout.write(current)
        # In order for this to work in various situations
        # We are requiring a new line to be entered at the end of
        # the current string being printed.  
        if current.rstrip(' ')[-1] != '\n':
            sys.stdout.write("\n")
        sys.stdout.flush()

    def get_wait_symbol(self):
        self.wait_index += 1
        if self.wait_index > len(self.wait_symbols) - 1:
            self.wait_index = 0
        return self.wait_symbols[self.wait_index]

    def print_progress(self, progress):
        current = ""
        if progress and progress.has_key("step") and progress["step"]:
            current += _("Step: %s\n") % (progress['step'])
            if "Downloading Items" in progress["step"]:
                current += self.form_progress_item_downloads(progress)
            else:
                current += "Waiting %s\n" % (self.get_wait_symbol())
            self._previous_step = progress["step"]
        else:
            current += "Waiting %s\n" % (self.get_wait_symbol())
            self._previous_step = None
        self.write(current, self._previous_progress)
        self._previous_progress = current

    def form_progress_item_details(self, details):
        result = ""
        for item_type in details:
            item_details = details[item_type]
            if item_details.has_key("num_success") and \
                item_details.has_key("total_count"):
                    result += _("%ss: %s/%s\n") % \
                        (item_type.title(),
                         item_details["num_success"],
                         item_details["total_count"])
        return result

    def form_progress_item_downloads(self, progress):
        current = ""
        bar_width = 25
        # calculate the progress
        done = float(progress['size_total']) - float(progress['size_left'])
        total = float(progress['size_total'])
        if total > 0.0:
            portion = done / total
        else:
            portion = 1.0
        percent = str(int(100 * portion))
        items_done = str(progress['items_total'] - progress['items_left'])
        items_total = str(progress['items_total'])
        # create the progress bar
        bar_ticks = '=' * int(bar_width * portion)
        bar_spaces = ' ' * (bar_width - len(bar_ticks))
        bar = '[' + bar_ticks + bar_spaces + ']'
        current += _('%s %s%%\n') % (bar, percent)
        current += self.form_progress_item_details(progress["details"])
        current += _("Total: %s/%s items\n") % (items_done, items_total)
        return current

    def form_error_details(self, progress, num_err_display=5):
        """
        progress : dictionary of sync progress info
        num_err_display: how many errors to display per type, if less than 0 will display all errors
        """
        ret_val = ""
        if not progress.has_key("error_details"):
            return ret_val
        error_entry = {}
        for errors in progress["error_details"]:
            item_info = errors[0]
            error_info = errors[1]
            if not error_entry.has_key(item_info["item_type"]):
                error_entry[item_info["item_type"]] = []
            if error_info and error_info.has_key("error"):
                error_entry[item_info["item_type"]].append(error_info["error"])
        for item_type in error_entry:
            ret_val += _("%s %s Error(s):\n") % (len(error_entry[item_type]), item_type.title())
            for index, errors in enumerate(error_entry[item_type]):
                if num_err_display > 0 and index >= num_err_display:
                    ret_val += _("\t... %s more error(s) occured.  See server logs for all errors.") % \
                            (len(error_entry[item_type]) - index)
                    break
                else:
                    ret_val += "\t" + str(errors) + "\n"
        return ret_val
# repo actions ----------------------------------------------------------------

class List(RepoAction):

    description = _('list available repositories')

    def setup_parser(self):
        self.parser.add_option("--groupid", action="append", dest="groupid",
                               help=_("filter repositories by group id"))

    def run(self):
        if self.opts.groupid:
            repos = self.repository_api.repositories_by_groupid(groups=self.opts.groupid)
        else:
            repos = self.repository_api.repositories()
        if not len(repos):
            system_exit(os.EX_OK, _("No repositories available to list"))
        print_header(_('List of Available Repositories'))
        for repo in repos:
            feedUrl = feedType = None
            if repo['source']:
                feedUrl = repo['source']['url']
                feedType = repo['source']['type']

            print constants.AVAILABLE_REPOS_LIST % (
                    repo["id"], repo["name"], feedUrl, feedType, repo["arch"],
                    repo["sync_schedule"], repo['package_count'],
                    repo['files_count'], ' '.join(repo['distributionid']) or None,
                    repo['publish'], repo['clone_ids'], repo['groupid'] or None)


class Status(RepoAction):

    description = _('show the status of a repository')

    def run(self):
        id = self.get_required_option('id')
        repo = self.get_repo(id)
        syncs = self.repository_api.sync_list(id)
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
            if syncs and syncs[0]['state'] in ('error'):
                print _("Last Error: %s\n%s") % \
                        (str(parse_date(syncs[0]['finish_time'])),
                                syncs[0]['traceback'][-1])
            return
        print _('Currently syncing:'),
        if syncs[0]['progress'] is None:
            print _('progress unknown')
        else:
            pkgs_left = syncs[0]['progress']['items_left']
            pkgs_total = syncs[0]['progress']['items_total']
            bytes_left = float(syncs[0]['progress']['size_left'])
            bytes_total = float(syncs[0]['progress']['size_total'])
            percent = 100.0
            if bytes_total > 0:
                percent = ((bytes_total - bytes_left) / bytes_total) * 100.0
            print _('%d%% done (%d of %d packages downloaded)') % \
                    (int(percent), (pkgs_total - pkgs_left), pkgs_total)


class Content(RepoAction):

    description = _('list the contents of a repository')

    def setup_parser(self):
        super(Content, self).setup_parser()
        opt_group = self.parser.add_option_group("Updates Only")
        opt_group.add_option("--updates", action="store_true", dest="updates",
                               help=_("only list available updates"))
        opt_group.add_option("--consumerid", dest="consumerid",
                               help=_("consumer id to list available updates."))
    def run(self):
        id = self.get_required_option('id')
        if self.opts.updates and not self.opts.consumerid:
            system_exit(os.EX_USAGE, _('Consumer Id is required with --updates option.'))
        repo = self.get_repo(id)
        all_packages = self.repository_api.packages(id)
        all_pnames = [pkg['filename'] for pkg in all_packages]
        all_errata = self.repository_api.errata(repo['id'])
        if self.opts.updates:
            consumerid = self.opts.consumerid
            errata_pkg_updates = self.consumer_api.errata_package_updates(consumerid)
            pkg_updates = errata_pkg_updates['packages']
            pkgs = []
            for p in pkg_updates:
                #limit updates to repo packages
                if p['filename'] in all_pnames:
                    pkgs.append(p['filename'])
            pnames = pkgs
            # limit errata to repo
            cerrata = errata_pkg_updates['errata']
            applicable_errata = []
            for e in cerrata:
                if e in all_errata:
                    applicable_errata.append(e)
            errata = applicable_errata
        else:
            pnames = all_pnames
            errata = all_errata
        print_header(_('Contents of %s') % id)

        print _('\nPackages in %s: \n') % id
        if not pnames:
            print _(' none')
        else:
            print '\n'.join(pnames[:])
        print _('\nErrata in %s: \n') % id
        if not errata:
            print _(' none')
        else:
            print '\n'.join(errata[:])
        print _('\nFiles in %s: \n') % id
        files = self.repository_api.list_files(repo['id'])
        if not files:
            print _(' none')
        else:
            for f in files:
                print ' ' + f['filename']
            


class Create(RepoAction):

    description = _('create a repository')

    def setup_parser(self):
        super(Create, self).setup_parser()
        self.parser.add_option("--name", dest="name",
                               help=_("common repository name"))
        self.parser.add_option("--arch", dest="arch",
                               help=_("package arch the repository should support"))
        self.parser.add_option("--feed", dest="feed",
                               help=_("url feed to populate the repository; feed format is type:url, where supported types include yum,rhn or local "))
        self.parser.add_option("--cacert", dest="cacert",
                               help=_("path location to ca certificate"))
        self.parser.add_option("--cert", dest="cert",
                               help=_("path location to entitlement certificate"))
        self.parser.add_option("--key", dest="key",
                               help=_("path location to entitlement certificate key"))
        self.parser.add_option("--schedule", dest="schedule",
                               help=_("cron entry date and time syntax for scheduling automatic repository synchronizations"))
        self.parser.add_option("--symlinks", action="store_true", dest="symlinks",
                               help=_("use symlinks instead of copying bits locally; applicable for local syncs"))
        self.parser.add_option("--relativepath", dest="relativepath",
                               help=_("relative path where the repository is stored and exposed to clients; this defaults to feed path if not specified"))
        self.parser.add_option("--groupid", action="append", dest="groupid",
                               help=_("a group to which the repository belongs; this is just a string identifier"))
        self.parser.add_option("--gpgkeys", dest="keys",
                               help=_("a ',' separated list of directories and/or files containing GPG keys"))
        self.parser.add_option("--checksum_type", dest="checksum_type", default="sha256",
                               help=_("checksum type to use when yum metadata is generated for this repo; default:sha256"))

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
        repo = self.repository_api.create(id, name, arch, feed, symlinks, schedule,
                                 cert_data=cert_data,
                                 relative_path=relative_path,
                                 groupid=groupid,
                                 gpgkeys=keylist, checksum_type=self.opts.checksum_type)
        print _("Successfully created repository [ %s ]") % repo['id']

class Clone(RepoProgressAction):

    description = _('clone a repository')

    def setup_parser(self):
        super(Clone, self).setup_parser()
        self.parser.add_option("--clone_id", dest="clone_id",
                               help=_("id of cloned repo (required)"))
        self.parser.add_option("--clone_name", dest="clone_name",
                               help=_("common repository name for cloned repo"))
        self.parser.add_option("--feed", dest="feed",
                               help=_("feed of cloned_repo: parent/origin/none"))
        self.parser.add_option("--groupid", dest="groupid",
                               help=_("a group to which the repository belongs; this is just a string identifier"))
        self.parser.add_option("--timeout", dest="timeout",
                               help=_("repository clone timeout"))
        self.parser.add_option('-F', '--foreground', dest='foreground',
                               action='store_true', default=False,
                               help=_('clone repository in the foreground'))

    def print_clone_finish(self, state, progress):
        self.print_progress(progress)
        current = ""
        current += "Clone: %s\n" % (state.title())
        current += "Item Details: \n"
        current += self.form_progress_item_details(progress["details"])
        if type(progress) == type({}):
            if progress.has_key("num_error") and progress['num_error'] > 0:
                current += _("Warning: %s errors occurred\n" % (progress['num_error']))
            if progress.has_key("error_details"):
                current += self.form_error_details(progress)
        self.write(current, self._previous_progress)
        self._previous_progress = current

    def clone_foreground(self, task):
        print _('You can safely CTRL+C this current command and it will continue')
        try:
            while task['state'] not in ('finished', 'error', 'timed out', 'canceled'):
                self.print_progress(task['progress'])
                time.sleep(0.25)
                task = self.repository_api.task_status(task['status_path'])
        except KeyboardInterrupt:
            print ''
            return
        self.print_clone_finish(task['state'], task['progress'])
        if task['state'] == 'error':
            raise SyncError(task['traceback'][-1])

    def get_task(self):
        id = self.get_required_option('id')
        self.get_repo(id)
        tasks = self.repository_api.sync_list(id)
        if tasks and tasks[0]['state'] in ('waiting', 'running'):
            print _('Sync for parent repository %s already in progress') % id
            return tasks[0]
        clone_id = self.get_required_option('clone_id')
        clone_name = self.opts.clone_name or clone_id
        feed = self.opts.feed or 'parent'
        groupid = self.opts.groupid
        timeout = self.opts.timeout
        task = self.repository_api.clone(id, clone_id=clone_id, clone_name=clone_name, feed=feed,
                                groupid=groupid, timeout=timeout)
        print _('Repository [%s] is being cloned as [%s]' % (id, clone_id))
        return task

    def run(self):
        foreground = self.opts.foreground
        task = self.get_task()
        if not foreground:
            system_exit(os.EX_OK, _('Use "repo status" to check on the progress'))
        self.clone_foreground(task)


class Delete(RepoAction):

    description = _('delete a repository')

    def run(self):
        id = self.get_required_option('id')
        self.repository_api.delete(id=id)
        print _("Successful deleted repository [ %s ]") % id


class Update(RepoAction):

    description = _('update a repository')

    # special options that are handled by the
    # specified methods.
    # format (option, method)
    OPTIONS = (
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
                               help=_("url feed to populate the repository (repository must be empty to change path component of the url)"))
        self.parser.add_option("--cacert", dest="ca",
                               help=_("path location to ca certificate"))
        self.parser.add_option("--cert", dest="cert",
                               help=_("path location to an entitlement certificate"))
        self.parser.add_option("--key", dest="key",
                               help=_("path location to an entitlement certificate's private key"))
        self.parser.add_option("--schedule", dest="sync_schedule",
                               help=_("cron entry date and time syntax for scheduling automatic repository synchronizations"))
        self.parser.add_option("--symlinks", dest="use_symlinks",
                               help=_("use symlinks instead of copying bits locally; applicable for local syncs (repository must be empty)"))
        self.parser.add_option("--relativepath", dest="relative_path",
                               help=_("relative path where the repository is stored and exposed to clients; this defaults to feed path if not specified (repository must be empty)"))
        self.parser.add_option("--groupid", dest="groupid",
                               help=_("a group to which the repository belongs; this is just a string identifier"))
        self.parser.add_option("--addkeys", dest="addkeys",
                               help=_("a ',' separated list of directories and/or files containing GPG keys"))
        self.parser.add_option("--rmkeys", dest="rmkeys",
                               help=_("a ',' separated list of GPG key names"))
    def run(self):
        id = self.get_required_option('id')
        delta = {}
        optdict = vars(self.opts)
        for k, v in optdict.items():
            if not v:
                continue
            method = self.find(k)
            if method: # special method
                method(id, v)
            else:
                delta[k] = v
        self.repository_api.update(delta)
        print _("Successfully updated repository [ %s ]") % id

    def find(self, option):
        """ find option specification """
        for opt, fn in self.OPTIONS:
            if opt == option:
                return getattr(self, fn)

    def addkeys(self, id, keylist):
        """ add the GPG keys """
        reader = KeyReader()
        keylist = reader.expand(keylist)
        self.repository_api.addkeys(id, keylist)

    def rmkeys(self, id, keylist):
        """ add the GPG keys """
        keylist = keylist.split(',')
        self.repository_api.rmkeys(id, keylist)

class Sync(RepoProgressAction):

    description = _('synchronize data to a repository from its feed')

    def setup_parser(self):
        super(Sync, self).setup_parser()
        self.parser.add_option("--timeout", dest="timeout",
                               help=_("synchronization timeout"))
        self.parser.add_option("--no-packages", action="store_true", dest="nopackages",
                               help=_("skip packages from the sync process"))
        self.parser.add_option("--no-errata", action="store_true", dest="noerrata",
                               help=_("skip errata from the sync process"))
        self.parser.add_option("--no-distribution", action="store_true", dest="nodistro",
                               help=_("skip distributions from the sync process"))
        self.parser.add_option('-F', '--foreground', dest='foreground',
                               action='store_true', default=False,
                               help=_('synchronize repository in the foreground'))

    def print_sync_finish(self, state, progress):
        self.print_progress(progress)
        current = ""
        current += _('Sync: %s\n') % (state.title())
        if state.title() in ('Finished'):
            if progress \
                    and progress.has_key("num_download") \
                    and progress.has_key("items_total"):
                current += _('%s/%s new items downloaded\n') % \
                    (progress['num_download'], progress['items_total'])
                current += _('%s/%s existing items processed\n') % \
                    ((progress['items_total'] - progress['num_download']), progress['items_total'])
        current += "\nItem Details: \n"
        if progress and progress.has_key("details"):
            current += self.form_progress_item_details(progress["details"])
        if type(progress) == type({}):
            if progress.has_key("num_error") and progress['num_error'] > 0:
                current += _("Warning: %s errors occurred\n" % (progress['num_error']))
            if progress.has_key("error_details"):
                current += self.form_error_details(progress)
        self.write(current, self._previous_progress)
        self._previous_progress = current

    def sync_foreground(self, task):
        print _('You can safely CTRL+C this current command and it will continue')
        try:
            while task['state'] not in ('finished', 'error', 'timed out', 'canceled'):
                self.print_progress(task['progress'])
                time.sleep(0.25)
                task = self.repository_api.task_status(task['status_path'])
        except KeyboardInterrupt:
            print ''
            return
        self.print_sync_finish(task['state'], task['progress'])
        if task['state'] == 'error':
            if task['traceback']:
                system_exit(-1, task['traceback'][-1])

    def get_task(self):
        id = self.get_required_option('id')
        self.get_repo(id)
        tasks = self.repository_api.sync_list(id)
        if tasks and tasks[0]['state'] in ('waiting', 'running'):
            print _('Sync for repository %s already in progress') % id
            return tasks[0]
        skip = {}
        if self.opts.nopackages:
            skip['packages'] = 1
            # skip errata as well, no point of errata without pkgs
            skip['errata'] = 1
        if self.opts.noerrata:
            skip['errata'] = 1
        if self.opts.nodistro:
            skip['distribution'] = 1
        timeout = self.opts.timeout
        task = self.repository_api.sync(id, skip, timeout)
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
        self.get_repo(id)
        syncs = self.repository_api.sync_list(id)
        if not syncs:
            system_exit(os.EX_OK, _('No sync to cancel'))
        task = syncs[0]
        if task['state'] not in ('waiting', 'running'):
            system_exit(os.EX_OK, _('Sync has completed'))
        taskid = task['id']
        self.repository_api.cancel_sync(str(id), str(taskid))
        print _("Sync for repository %s canceled") % id

class Schedules(RepoAction):

    description = _('list all repository schedules')

    def setup_parser(self):
        pass

    def run(self):
        print_header(_('Available Repository Schedules'))
        schedules = self.repository_api.all_schedules()
        for id in schedules.keys():
            print(constants.REPO_SCHEDULES_LIST % (id, schedules[id]))

class ListKeys(RepoAction):

    description = _('list gpg keys')

    def run(self):
        id = self.get_required_option('id')
        for key in self.repository_api.listkeys(id):
            print os.path.basename(key)

class Publish(RepoAction):
    description = _('enable/disable repository being published by apache')

    def setup_parser(self):
        super(Publish, self).setup_parser()
        self.parser.add_option("--disable", dest="disable", action="store_true",
                default=False, help=_("disable publish for this repository"))
        self.parser.add_option("--enable", dest="enable", action="store_true",
                default=False, help=_("enable publish for this repository"))

    def run(self):
        id = self.get_required_option('id')
        if self.opts.enable and self.opts.disable:
            system_exit(os.EX_USAGE, _("Error, both enable and disable are set to True"))
        if not self.opts.enable and not self.opts.disable:
            system_exit(os.EX_USAGE, _("Error, either --enable or --disable needs to be chosen"))
        if self.opts.enable:
            state = True
        if self.opts.disable:
            state = False
        if self.repository_api.update_publish(id, state):
            print _("Repository [%s] 'published' has been set to [%s]") % (id, state)
        else:
            print _("Unable to set 'published' to [%s] on repository [%s]") % (state, id)


class AddPackages(RepoAction):
    description = _('Add specific package(s) from the source repository.')

    def setup_parser(self):
        super(AddPackages, self).setup_parser()
        self.parser.add_option("-p", "--package", action="append", dest="pkgname",
                help=_("Package filename to add to this repository"))
        self.parser.add_option("--source", dest="srcrepo",
            help=_("Source repository with specified packages to perform add"))
        self.parser.add_option("--csv", dest="csv",
                help=_("A csv file to perform batch operations on. Format:filename,checksum"))
        self.parser.add_option("-y", "--assumeyes", action="store_true", dest="assumeyes",
                            help=_("Assume yes; automatically process dependencies as part of add operation."))
        self.parser.add_option("-r", "--recursive", action="store_true", dest="recursive",
                            help=_("Recursively lookup the dependency list; defaults to one level of lookup."))

    def run(self):
        id = self.get_required_option('id')

        if not self.opts.pkgname and not self.opts.csv:
            system_exit(os.EX_USAGE, _("Error, atleast one package id is required to perform an add."))
        if self.opts.pkgname and self.opts.csv:
            system_exit(os.EX_USAGE, _("Both --package and --csv cannot be used in the same command."))
        # check if repos are valid
        self.get_repo(id)
        if self.opts.srcrepo:
            self.get_repo(self.opts.srcrepo)
        # lookup requested pkgs in the source repository
        pnames = []
        pids = []
        if self.opts.csv:
            if not os.path.exists(self.opts.csv):
                system_exit(os.EX_DATAERR, _("CSV file [%s] not found"))
            pkglist = utils.parseCSV(self.opts.csv)
        else:
            pkglist = self.opts.pkgname
        for pkginfo in pkglist:
            if isinstance(pkginfo, list) and len(pkginfo) == 2:
                #default to sha256
                pkg, checksum = pkginfo
            else:
                checksum_type = None
                pkg, checksum = pkginfo, None
            if self.opts.srcrepo:
                src_pkgobj = self.lookup_repo_packages(pkg, self.opts.srcrepo,
                                                       checksum=checksum)
                if not src_pkgobj: # not in src_pkgobjs:
                    print(_("Package %s could not be found skipping" % pkg))
                    continue
            else:
                src_pkgobj = self.service_api.search_packages(filename=pkg)
                if not src_pkgobj:
                    print(_("Package %s could not be found skipping" % pkg))
                    continue
                if len(src_pkgobj) > 1:
                    msg = _("There is more than one file with filename [%s]. \
                            Please use csv option to include checksum.; Skipping add" % pkg)
                    log.error(msg)
                    print msg
                    continue
                src_pkgobj = src_pkgobj[0]
            tgt_pkgobj = self.lookup_repo_packages(pkg, id, checksum=checksum)
            if tgt_pkgobj:
                print (_("Package [%s] are already part of repo [%s]. skipping" % (pkg, id)))
                continue
            name = "%s-%s-%s.%s" % (src_pkgobj['name'], src_pkgobj['version'],
                                    src_pkgobj['release'], src_pkgobj['arch'])
            pnames.append(name)
            pids.append(src_pkgobj['id'])

        if not pnames:
            system_exit(os.EX_DATAERR)
        if self.opts.srcrepo:
            # lookup dependencies and let use decide whether to include them
            pkgdeps = self.handle_dependencies(self.opts.srcrepo, id, pnames, self.opts.recursive, self.opts.assumeyes)
            for pdep in pkgdeps:
                pnames.append("%s-%s-%s.%s" % (pdep['name'], pdep['version'], pdep['release'], pdep['arch']))
                pids.append(pdep['id'])
        else:
            print _("No Source repo specified, skipping dependency lookup")
        try:
            self.repository_api.add_package(id, pids)
        except Exception:
            system_exit(os.EX_DATAERR, _("Unable to add package [%s] to repo [%s]" % (pnames, id)))
        print _("Successfully added packages %s to repo [%s]." % (pnames, id))

class RemovePackages(RepoAction):
    description = _('Remove package(s) from the repository.')

    def setup_parser(self):
        super(RemovePackages, self).setup_parser()
        self.parser.add_option("-p", "--package", action="append", dest="pkgname",
                help=_("Package filename to remove from this repository"))
        self.parser.add_option("--csv", dest="csv",
                help=_("A csv file to perform batch operations on. Format:filename,checksum"))
        self.parser.add_option("-y", "--assumeyes", action="store_true", dest="assumeyes",
                            help=_("Assume yes; automatically process dependencies as part of remove operation."))
        self.parser.add_option("-r", "--recursive", action="store_true", dest="recursive",
                            help=_("Recursively lookup the dependency list; defaults to one level of lookup."))

    def run(self):
        id = self.get_required_option('id')
        if not self.opts.pkgname and not self.opts.csv:
            system_exit(os.EX_USAGE, _("Error, atleast one package id is required to perform a delete."))
        if self.opts.pkgname and self.opts.csv:
            system_exit(os.EX_USAGE, _("Both --package and --csv cannot be used in the same command."))
        # check if repo is valid
        self.get_repo(id)
        pnames = []
        pobj = []
        if self.opts.csv:
            if not os.path.exists(self.opts.csv):
                system_exit(os.EX_DATAERR, _("CSV file [%s] not found"))
            pkglist = utils.parseCSV(self.opts.csv)
        else:
            pkglist = self.opts.pkgname
        for pkginfo in pkglist:
            if isinstance(pkginfo, list) and len(pkginfo) == 2:
                pkg, checksum = pkginfo
            else:
                pkg, checksum = pkginfo, None
            src_pkgobj = self.lookup_repo_packages(pkg, id, checksum)
            if not src_pkgobj:
                print(_("Package %s could not be found skipping" % pkg))
                continue
            name = "%s-%s-%s.%s" % (src_pkgobj['name'], src_pkgobj['version'],
                                    src_pkgobj['release'], src_pkgobj['arch'])
            pnames.append(name)
            pobj.append(src_pkgobj)
        if not pnames:
            system_exit(os.EX_DATAERR)
        pkgdeps = self.handle_dependencies(id, None, pnames, self.opts.recursive, self.opts.assumeyes)
        pobj += pkgdeps
        pkg = list(set([p['filename'] for p in pobj]))
        try:
            self.repository_api.remove_package(id, pobj)
            print _("Successfully removed package %s from repo [%s]." % (pkg, id))
        except Exception:
            print _("Unable to remove package [%s] to repo [%s]" % (pkg, id))


class AddErrata(RepoAction):
    description = _('Add specific errata from the source repository')

    def setup_parser(self):
        super(AddErrata, self).setup_parser()
        self.parser.add_option("-e", "--errata", action="append", dest="errataid",
                help=_("Errata Id to add to this repository"))
        self.parser.add_option("--source", dest="srcrepo",
            help=_("Source repository with specified packages to perform add"))
        self.parser.add_option("-y", "--assumeyes", action="store_true", dest="assumeyes",
                            help=_("Assume yes; automatically process dependencies as part of remove operation."))
        self.parser.add_option("-r", "--recursive", action="store_true", dest="recursive",
                            help=_("Recursively lookup the dependency list; defaults to one level of lookup."))

    def run(self):
        id = self.get_required_option('id')
        if not self.opts.errataid:
            system_exit(os.EX_USAGE, _("Error, atleast one erratum id is required to perform an add."))
        if not self.opts.srcrepo:
            system_exit(os.EX_USAGE, _("Error, a source respository where erratum exists is required"))
        # check if repos are valid
        self.get_repo(id)
        self.get_repo(self.opts.srcrepo)
        errataids = self.opts.errataid
        effected_pkgs = []
        for eid in errataids:
            e_repos = self.errata_api.find_repos(eid) or []
            if id in e_repos:
                print(_("Errata Id [%s] is already in target repo [%s]. skipping" % (eid, id)))
                continue
            if self.opts.srcrepo not in e_repos:
                print(_("Errata Id [%s] is not in source repo [%s]. skipping" % (eid, self.opts.srcrepo)))
                continue
            erratum = self.errata_api.erratum(eid)
            if not erratum:
                print(_("Errata Id [%s] could not be found. skipping" % eid))
                continue
            effected_pkgs += [str(pinfo['filename'])
                         for pkg in erratum['pkglist']
                         for pinfo in pkg['packages']]

        if not effected_pkgs:
            system_exit(os.EX_DATAERR)

        pnames = []
        for pkg in effected_pkgs:
            src_pkgobj = self.lookup_repo_packages(pkg, self.opts.srcrepo)
            if not src_pkgobj: # not in src_pkgobjs:
                log.info("Errata Package %s could not be found in source repo. skipping" % pkg)
                continue
            name = "%s-%s-%s.%s" % (src_pkgobj['name'], src_pkgobj['version'],
                                    src_pkgobj['release'], src_pkgobj['arch'])
            pnames.append(name)

        # lookup dependencies and let use decide whether to include them
        pkgdeps = self.handle_dependencies(self.opts.srcrepo, id, pnames, self.opts.recursive, self.opts.assumeyes)
        pids = [pdep['id'] for pdep in pkgdeps]
        try:
            self.repository_api.add_errata(id, errataids)
            if pids:
                # add dependencies to repo
                self.repository_api.add_package(id, pids)
            print _("Successfully added Errata %s to repo [%s]." % (errataids, id))
        except Exception:
            system_exit(os.EX_DATAERR, _("Unable to add errata [%s] to repo [%s]" % (errataids, id)))


class RemoveErrata(RepoAction):
    description = _('Remove errata from the repository')

    def setup_parser(self):
        super(RemoveErrata, self).setup_parser()
        self.parser.add_option("-e", "--errata", action="append", dest="errataid",
                help=_("Errata Id to delete from this repository"))
        self.parser.add_option("-y", "--assumeyes", action="store_true", dest="assumeyes",
                            help=_("Assume yes; automatically process dependencies as part of remove operation."))
        self.parser.add_option("-r", "--recursive", action="store_true", dest="recursive",
                            help=_("Recursively lookup the dependency list; defaults to one level of lookup."))

    def run(self):
        id = self.get_required_option('id')
        # check if repo is valid
        self.get_repo(id)
        if not self.opts.errataid:
            system_exit(os.EX_USAGE, _("Error, atleast one erratum id is required to perform a delete."))
        errataids = self.opts.errataid
        effected_pkgs = []
        for eid in errataids:
            e_repos = self.errata_api.find_repos(eid)

            if id not in e_repos:
                print(_("Errata Id [%s] is not in the repo [%s]. skipping" % (eid, id)))
                continue
            erratum = self.errata_api.erratum(eid)
            if not erratum:
                print(_("Errata Id [%s] could not be found. skipping" % eid))
                continue
            effected_pkgs += [str(pinfo['filename'])
                         for pkg in erratum['pkglist']
                         for pinfo in pkg['packages']]
        if not effected_pkgs:
            system_exit(os.EX_DATAERR)
        pobj = []
        pnames = []
        for pkg in effected_pkgs:
            src_pkgobj = self.lookup_repo_packages(pkg, id)
            if not src_pkgobj:
                log.info("Package %s could not be found skipping" % pkg)
                continue
            name = "%s-%s-%s.%s" % (src_pkgobj['name'], src_pkgobj['version'],
                                    src_pkgobj['release'], src_pkgobj['arch'])
            pnames.append(name)
            pobj.append(src_pkgobj)
        if not pnames:
            system_exit(os.EX_DATAERR, \
                        _("Associated Errata packages for id [%s] are not in the repo." % errataids))

        # lookup dependencies and let use decide whether to include them
        pkgdeps = self.handle_dependencies(id, None, pnames, self.opts.recursive, self.opts.assumeyes)
        try:
            self.repository_api.delete_errata(id, errataids)
            if pkgdeps:
                self.repository_api.remove_package(id, pkgdeps)
        except Exception:
            print _("Unable to remove errata [%s] to repo [%s]" % (errataids, id))
        print _("Successfully removed Errata %s from repo [%s]." % (errataids, id))


class AddFiles(RepoAction):
    description = _('Add file(s) from a repository.')

    def setup_parser(self):
        super(AddFiles, self).setup_parser()
        self.parser.add_option("-f", "--file", action="append", dest="files",
                help=_("file to add to this repository"))
        self.parser.add_option("--source", dest="srcrepo",
            help=_("Source repository with specified files to perform add (optional)"))
        self.parser.add_option("--csv", dest="csv",
                help=_("A csv file to perform batch operations on. Format:filename,checksum"))

    def run(self):
        id = self.get_required_option('id')
        # check if repos are valid
        self.get_repo(id)
        if self.opts.srcrepo:
            self.get_repo(self.opts.srcrepo)
        fids = {}
        if self.opts.files and self.opts.csv:
            system_exit(os.EX_USAGE, _("Both --files and --csv cannot be used in the same command."))
        if self.opts.csv:
            if not os.path.exists(self.opts.csv):
                system_exit(os.EX_DATAERR, _("CSV file [%s] not found"))
            flist = utils.parseCSV(self.opts.csv)
        else:
            if not self.opts.files:
                system_exit(os.EX_USAGE, _("Error, atleast one file is required to perform an add."))
            flist = self.opts.files
        for f in flist:
            if isinstance(f, list) or len(f) == 2:
                filename, checksum = f
                if not len(f) == 2:
                    log.error("Bad format [%s] in csv, skipping" % f)
                    continue
            else:
                filename, checksum = f, None

            fobj = self.service_api.search_file(filename=filename, checksum=checksum)
            if not len(fobj):
                print _("File [%s] could not be found on server; Skipping add" % filename)
                continue
            if len(fobj) > 1:
                if not self.opts.csv: 
                    print fobj
                    print _("There is more than one file with filename [%s]. Please use csv option to include checksum.; Skipping remove" % filename)
                    continue
                else:
                    for fo in fobj:
                        if fo['filename'] == filename and fo['checksum']['sha256'] == checksum:
                            fids[filename] = fo
            else:
                fids[filename] = fobj[0]

        for fname, fobj in fids.items():
            if self.opts.srcrepo and not self.opts.srcrepo in fobj["repos"]:
                print _("File [%s] Could not be found in the repo [%s]" % (filename, self.opts.srcrepo))
                continue
            try:
                self.repository_api.add_file(id, [fobj['id']])
            except Exception:
                raise
                print _("Unable to add package [%s] to repo [%s]" % (fname, id))
                continue
            print _("Successfully added packages %s to repo [%s]." % (fname, id))

class RemoveFiles(RepoAction):
    description = _('Remove file(s) from a repository.')

    def setup_parser(self):
        super(RemoveFiles, self).setup_parser()
        self.parser.add_option("-f", "--file", action="append", dest="files",
                help=_("file to remove from this repository"))
        self.parser.add_option("--csv", dest="csv",
                help=_("A csv file to perform batch operations on. Format:filename,checksum"))
        self.parser.add_option("--purge-files", action="store_true",dest="purge_files",
                help=_("Remove files from filesystem on server (optional)"))


    def run(self):
        id = self.get_required_option('id')
        # check if repos are valid
        self.get_repo(id)
        if self.opts.files and self.opts.csv:
            system_exit(os.EX_USAGE, _("Error: Both --files and --csv cannot be used in the same command."))
        keep_files=True
        if self.opts.purge_files:
            keep_files = False
        fids = {}
        if self.opts.csv:
            if not os.path.exists(self.opts.csv):
                system_exit(os.EX_DATAERR, _("CSV file [%s] not found"))
            flist = utils.parseCSV(self.opts.csv)
        else:
            if not self.opts.files:
                system_exit(os.EX_USAGE, _("Error, atleast one file is required to perform an remove."))
            flist = self.opts.files
        for f in flist:
            if isinstance(f, list) or len(f) == 2:
                filename, checksum = f
                if not len(f) == 2:
                    log.error("Bad format [%s] in csv, skipping" % f)
                    continue
            else:
                filename, checksum = f, None
            fobj = self.service_api.search_file(filename=filename, checksum=checksum)
            if not len(fobj):
                print _("File [%s] could not be found on server; Skipping remove" % filename)
                continue
            if len(fobj) > 1:
                if not self.opts.csv:
                    print fobj
                    print _("There is more than one file with filename [%s]. Please use csv option to include checksum.; Skipping remove" % filename)
                    continue
                else:
                    for fo in fobj:
                        print fo['filename'], checksum
                        if fo['filename'] == filename and fo['checksum']['sha256'] == checksum:
                            fids[filename] = fo['id']
            else:
                fids[filename] = fobj[0]['id']
        for fname, fid in fids.items():
            try:
                self.repository_api.remove_file(id, [fid], keep_files=keep_files)
            except Exception:
                raise
                system_exit(os.EX_DATAERR, _("Unable to remove file [%s] from repo [%s]" % (fname, id)))
            print _("Successfully removed file [%s] from repo [%s]." % (fname, id))


# repo command ----------------------------------------------------------------

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
