from gettext import gettext as _
import logging
import os
import time
import uuid
import shutil

import kobo.shortcuts
import mongoengine

from pulp.common import dateutils
from pulp.plugins.util.publish_step import PublishStep
from pulp.server.config import config as pulp_config
from pulp.server.exceptions import PulpCodedException
from pulp.server.db.model.repository import RepoPublishResult
from pulp.server.db.model import Distributor


ASSOCIATED_UNIT_DATE_KEYWORD = "created"
START_DATE_KEYWORD = 'start_date'
END_DATE_KEYWORD = 'end_date'

_logger = logging.getLogger(__name__)


class RSyncPublishStep(PublishStep):

    _CMD = "rsync"
    # recursive, symlinks, timestamps, keep dir links, omit dir times, compress, itemize
    _AZQ = "-rtKOzi"

    def __init__(self, step_type, file_list, src_directory, dest_directory, config=None,
                 exclude=[], delete=False, links=False):
        """
        Copies files using rsync to a remote server and filesystem location defined in the
        distributor config.

        :param step_type: Name of step
        :type step_type: str
        :param file_list: list of paths relative to src_directory
        :type file_list: list
        :param src_directory: absolute path to directory which contains all items in file_list
        :type src_directory: str
        :param dest_directory: path to directory relative to remote root where files should be
               rsynced
        :type dest_directory: str
        :param config: distributor configuration
        :type config: pulp.plugins.config.PluginCallConfiguration
        :param exclude: list of files/directories to skip
        :type exclude: list of str
        :param delete: determines if --delete is passed to rsync
        :type delete: bool
        :param links: if true, --links is passed to rsync
        :type links: bool
        """
        super(PublishStep, self).__init__(step_type, config=config)
        self.description = _('Rsync files to remote destination')
        self.file_list = file_list
        self.exclude = exclude
        self.delete = delete
        self.src_directory = src_directory
        self.dest_directory = dest_directory
        self.links = links

    def remote_mkdir(self, path):
        """
        Creates path on remote server. The path is rooted in distributor's remote_root directory.

        :param path: path to create on remote server
        :type path: str

        :return: (return code from rsync, string made up of stdout and stderr from running rsync
                  to create remote directory)
        :rtype: tuple
        """
        tmpdir = os.path.join(self.get_working_dir(), '.tmp')
        os.makedirs(os.path.join(tmpdir, path.lstrip("/")))
        args = ['rsync', '-avrK', '-f+ */']
        args.extend(self.make_authentication())
        args.append("%s/" % tmpdir)
        args.append(self.make_destination(path).replace(str(path), ""))
        _logger.debug("remote mkdir: %s" % args)
        is_ok, output = self.call(args, include_args_in_output=True)
        _logger.debug("remote mkdir out: %s" % output)
        shutil.rmtree(tmpdir)
        return is_ok, output

    def make_ssh_cmd(self, args=None):
        """
        Returns a list of arguments needed to form an ssh command for connecting to remote server.

        :param args:list of extra args to append to the standard ssh command
        :type args: list

        :return: list of arguments for ssh portion of command
        :rtype: list
        """
        user = self.get_config().flatten()["remote"]['ssh_user']
        # -e 'ssh -l ssh_user -i ssh_identity_file'
        # use shared ssh connection for other threads
        cmd = ['ssh', '-l', user]
        key = self.get_config().flatten()["remote"]['ssh_identity_file']
        cmd += ['-i', key,
                '-o', 'StrictHostKeyChecking no',
                '-o', 'UserKnownHostsFile /dev/null']
        if args:
            cmd += args
        return cmd

    def make_authentication(self):
        """
        Returns a list of strings representing args for command for authenticating against a remote
        server.

        :return: list of arguments for auth. e.g., ['-e',  'ssh, '-l', 'ssh_user', '-i',
                                                    '/ssh_identity_file', 'hostname']
        :rtype: list
        """
        ssh_parts = []
        for arg in self.make_ssh_cmd():
            if " " in arg:
                ssh_parts.append('"%s"' % arg)
            else:
                ssh_parts.append(arg)

        return ['-e', " ".join(ssh_parts)]

    def make_full_path(self, relative_path):
        """
        Returns absolute path of a relative path on the remote server.

        :param relative_path: relative path
        :type relative_path: str

        :return: absolute path to the relative path
        :rtype: str
        """
        return os.path.join(self.get_config().flatten()['remote']['root'], relative_path)

    def make_destination(self, relative_path):
        """
        Parse from self.config information to make up a hostname and remote path used for rsync
        command.

        :param relative_path: path relative to the root configured in distributor
        :type relative_path: str

        :return: str of the combination of user, host, and dir.
        :rtype:  str
        """
        user = self.get_config().flatten()["remote"]['ssh_user']
        host = self.get_config().flatten()["remote"]['host']
        remote_root = self.get_config().flatten()["remote"]['root']
        return '%s@%s:%s' % (user, host, os.path.join(remote_root, relative_path))

    def call(self, args, include_args_in_output=True):
        """
        A wrapper around kobo.shortcuts.run. If ssh_exchange_identification or
        max-concurrent-connections exceptions are thrown by ssh, up to 10 retries follows.

        :param args: list of args for rsync
        :type args: list
        :param include_args_in_output: include the rsync arguments in output or not
        :type include_args_in_output: bool

        :return: (boolean indicating success or failure, output from rsync command)
        :rtype: tuple of boolean and string
        """
        for t in xrange(10):
            rv, out = kobo.shortcuts.run(cmd=args, can_fail=True)
            possible_known_exceptions = \
                ("ssh_exchange_identification:" in out) or ("max-concurrent-connections=25" in out)
            if not (rv and possible_known_exceptions):
                break
            _logger.info(_("Connections limit reached, trying once again in thirty seconds."))
            time.sleep(30)
        if include_args_in_output:
            message = "%s\n%s" % (args, out)
        else:
            message = out
        return (rv == 0, message)

    def make_rsync_args(self, files_from, source_prefix, dest_prefix, exclude=None):
        """
        Creates a list of arguments for the rsync command

        :param files_from: absolute path to a file with list of file paths to rsync
        :type files_from: str
        :param source_prefix: path to directory that contains all paths in files_from
        :type source_prefix: str
        :param dest_prefix: path to directory on remote server where files should be rsynced
        :type dest_prefix: str
        :param exclude: list of file/directory paths to exclude
        :type exclude: list

        :return: list of arguments for rsync command
        :rtype: list of strings
        """
        args = [self._CMD, self._AZQ]
        if not self.delete:
            args.extend(["--files-from", files_from, "--relative"])

        if exclude:
            for x in exclude:
                args.extend(["--exclude", x])
        args.extend(self.make_authentication())
        if self.delete:
            args.append("--delete")
        if self.links:
            args.append("--links")
        else:
            args.append("--copy-links")
        args.append(source_prefix)
        args.append(self.make_destination(dest_prefix))
        return args

    def rsync(self):
        """
        This method formulates the rsync command based on parameters passed in to the __init__ and
        then executes it.

        :return: (boolean indicating success or failure, str made up of stdout and stderr
                  generated by rsync command)
        :rtype: tuple
        """
        if not self.file_list and not self.delete:
            return (True, _("Nothing to sync"))
        if not os.path.exists(self.src_directory):
            os.makedirs(self.src_directory)

        output = ""
        list_of_files = os.path.join(self.get_working_dir(), str(uuid.uuid4()))
        open(list_of_files, 'w').write("\n".join(sorted(self.file_list)))

        # copy files here, not symlinks
        (is_successful, this_output) = self.remote_mkdir(self.dest_directory)
        if not is_successful:
            params = {'directory': self.dest_directory, 'output': this_output}
            _logger.error(_("Cannot create directory %(directory)s: %(output)s") % params)
            return (is_successful, this_output)
        output += this_output
        rsync_args = self.make_rsync_args(list_of_files, self.src_directory,
                                          self.dest_directory, self.exclude)
        (is_successful, this_output) = self.call(rsync_args)
        _logger.info(this_output)
        if not is_successful:
            _logger.error(this_output)
            return (is_successful, this_output)
        output += this_output
        return (is_successful, output)

    def process_main(self):
        """
        This method is the main method executed when the step system executes a step.
        """
        (successful, output) = self.rsync()
        if not successful:
            raise PulpCodedException(message=output)


class UpdateLastPredistDateStep(PublishStep):
    """
    After a publish of the Predistributor completes, store the date in the scratchpad.
    """
    def __init__(self, distributor, predist_pub_date):
        super(UpdateLastPredistDateStep, self).__init__("UpdateLastPredistDate")
        self.distributor = distributor
        self.date = predist_pub_date

    def process_main(self):
        """
        Save last_predist_last_published.
        """
        if "scratchpad" not in self.distributor:
            self.distributor["scratchpad"] = {}

        self.distributor["scratchpad"]["last_predist_last_published"] = self.date

        self.get_conduit().set_scratchpad(self.distributor["scratchpad"])


class Publisher(PublishStep):
    """
    RSync publisher class that provides the common code for publishing to remote server. Each
    plugin needs to extend this class and add necesary logic to the _add_necesary_steps method.
    """
    def __init__(self, repo, publish_conduit, config, distributor_type):
        """
        :param repo: Pulp managed Yum repository
        :type  repo: pulp.plugins.model.Repository
        :param publish_conduit: Conduit providing access to relative Pulp functionality
        :type  publish_conduit: pulp.plugins.conduits.repo_publish.RepoPublishConduit
        :param config: Pulp configuration for the distributor
        :type  config: pulp.plugins.config.PluginCallConfiguration
        :param distributor_type: The type of the distributor that is being published
        :type distributor_type: str

        :ivar last_published: last time this distributor published the repo
        :ivar last_delete: last time a unit was removed from this repository
        :ivar repo: repository being operated on
        :ivar predistributor: distributor object that is associated with this distributor. It's
                              publish history affects the type of publish is performed
        :ivar symlink_list: list of symlinks to rsync
        :ivar content_unit_file_list: list of content units to rsync
        :ivar symlink_src: path to directory containing all symlinks
        """

        super(Publisher, self).__init__("Repository publish", repo,
                                        publish_conduit, config,
                                        distributor_type=distributor_type)

        self.distributor = Distributor.objects.get_or_404(
            repo_id=self.repo.id,
            distributor_id=publish_conduit.distributor_id)
        self.last_published = self.distributor["last_publish"]
        self.last_deleted = repo.last_unit_removed
        self.repo = repo
        self.predistributor = self._get_predistributor()

        self.last_predist_last_published = None
        if self.predistributor:
            scratchpad = self.distributor.scratchpad or {}
            self.last_predist_last_published = scratchpad.get("last_predist_last_published")

        if self.last_published:
            string_date = dateutils.format_iso8601_datetime(self.last_published)
        else:
            string_date = None

        if self.predistributor:
            search_params = {'repo_id': repo.id,
                             'distributor_id': self.predistributor["distributor_id"],
                             'started': {"$gte": string_date}}
            self.predist_history = RepoPublishResult.get_collection().find(search_params)
        else:
            self.predist_history = []

        self.remote_path = self.get_remote_repo_path()

        if self.is_fastforward():
            start_date = self.last_predist_last_published
            end_date = None

            if self.predistributor:
                end_date = self.predistributor["last_publish"]

            date_filter = self.create_date_range_filter(start_date=start_date, end_date=end_date)
        else:
            date_filter = None

            if self.predistributor:
                end_date = self.predistributor["last_publish"]
                date_filter = self.create_date_range_filter(None, end_date=end_date)

        self.symlink_list = []
        self.content_unit_file_list = []
        self.symlink_src = os.path.join(self.get_working_dir(), '.relative/')

        self._add_necesary_steps(date_filter=date_filter, config=config)

    def is_fastforward(self):
        """
        This method checks whether this publish should be a fastforward publish.

        :return: Whether or not this publish should be in fast forward mode
        :rtype: bool
        """
        force_full = False
        for entry in self.predist_history:
            predistributor_force_full = entry.get("distributor_config", {}).get("force_full",
                                                                                False)
            force_full |= predistributor_force_full
            if entry.get("result", "error") == "error":
                force_full = True

        if self.last_published:
            last_published = self.last_published.replace(tzinfo=None)
        else:
            last_published = None

        if self.last_deleted:
            last_deleted = self.last_deleted.replace(tzinfo=None)
        else:
            last_deleted = None

        config_force_full = self.get_config().get("force_full", False)
        force_full = force_full | config_force_full
        delete = self.get_config().get("delete", False)

        return not force_full and not delete and self.last_predist_last_published and \
            ((last_deleted and last_published and last_published > last_deleted) or not last_deleted)

    def create_date_range_filter(self, start_date=None, end_date=None):
        """
        Create a date filter based on start and end issue dates specified in the repo config.

        :param start_date: start time for the filter
        :type  start_date: datetime.datetime
        :param end_date: end time for the filter
        :type  end_date: datetime.datetime

        :return: Q object with start and/or end dates, or None if start and end dates are not
                 provided
        :rtype:  mongoengine.Q or types.NoneType
        """
        if start_date:
            start_date = dateutils.format_iso8601_datetime(start_date)
        if end_date:
            end_date = dateutils.format_iso8601_datetime(end_date)

        if start_date and end_date:
            return mongoengine.Q(created__gte=start_date, created__lte=end_date)
        elif start_date:
            return mongoengine.Q(created__gte=start_date)
        elif end_date:
            return mongoengine.Q(created__lte=end_date)

    def get_remote_repo_path(self):
        """
        Returns the full path to the published repository on remote server.

        :return: relative url for the repo on remote server
        :rtype: str
        """
        if "relative_url" in self.repo.notes and self.repo.notes["relative_url"]:
            return self.repo.notes["relative_url"]
        else:
            return self.repo.id

    def get_master_directory(self):
        """
        Returns path to master directory of the predistributor.

        :return: path to 'master' publish directory
        :rtype: str
        """
        repo_relative_path = self.predistributor['config'].get('relative_url', self.repo.id)
        return os.path.realpath(os.path.join(self._get_root_publish_dir(), repo_relative_path))

    def get_units_directory_dest_path(self):
        """
        Returns the path on the remote server where content units should be stored.

        :return: relative path to the directory where content units remote server
        :rtype: str
        """

        if self.get_config().get("remote_units_path"):
            origin_dest_prefix = self.get_config().get("remote_units_path")
        else:
            origin_dest_prefix = os.path.join("content", "units")
        return origin_dest_prefix

    def get_units_src_path(self):
        return os.path.join(pulp_config.get('server', 'storage_dir'), 'content', 'units')

    def _add_necesary_steps(self, date_filter=None):
        """
        This method needs to be implemented in each plugin. This method should include calls to
        self.add_child() with particular rsync steps that are needed to perform the full publish
        to the remote server.

        :param date_filter:  Q object with start and/or end dates, or None if start and end dates
                             are not provided
        :type date_filter:  mongoengine.Q or types.NoneType
        """
        raise NotImplementedError()

    def _get_root_publish_dir(self):
        """
        Returns the publish directory path for the predistributor

        :return: path to the publish directory of the predistirbutor
        :rtype: str
        """
        raise NotImplementedError()

    def _get_predistributor(self):
        """
        Returns distributor which repo has to be published in before
        publish in rsync distributor, content generator.

        :return: predistributor that was configured in rsyn distributor's config
        :rtype: Distributor
        """
        return None
