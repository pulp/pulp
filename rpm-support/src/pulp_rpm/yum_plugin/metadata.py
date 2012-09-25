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

import commands
import gzip
import os
import shlex
import shutil
import subprocess
import threading
import signal
import time

import rpmUtils
from createrepo import MetaDataGenerator, MetaDataConfig
from createrepo import yumbased, GzipFile

from pulp_rpm.yum_plugin import util
from pulp.common.util import encode_unicode, decode_unicode

_LOG = util.getLogger(__name__)
__yum_lock = threading.Lock()

# In memory lookup table for createrepo processes
# Responsible for 2 tasks.  1) Restrict only one createrepo per repo_dir, 2) Allow an async cancel of running createrepo
CREATE_REPO_PROCESS_LOOKUP = {}
CREATE_REPO_PROCESS_LOOKUP_LOCK = threading.Lock()
DEFAULT_CHECKSUM = "sha256"

class CreateRepoError(Exception):
    pass


class CreateRepoAlreadyRunningError(Exception):
    pass


class ModifyRepoError(CreateRepoError):
    pass


class CancelException(Exception):
    pass


def set_progress(type_id, status, progress_callback):
    if progress_callback:
        progress_callback(type_id, status)


def generate_metadata(repo_working_dir, publish_conduit, config, progress_callback=None, groups_xml_path=None):
    """
      NOTE: This method will be deprecated in future; use metadata.generate_yum_metadata call instead

      build all the necessary info and invoke createrepo to generate metadata

      @param repo_working_dir: rpository working directory where metadata is written
      @type  repo_working_dir: str

      @param config: plugin configuration
      @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

      @param progress_callback: callback to report progress info to publish_conduit
      @type  progress_callback: function

      @param groups_xml_path: path to the package groups/package category comps info
      @type groups_xml_path: str

      @return True on success, False on error
      @rtype bool
    """
    errors = []
    metadata_progress_status = {"state" : "IN_PROGRESS"}
    repo_dir = repo_working_dir
    checksum_type = get_repo_checksum_type(publish_conduit, config)
    skip_metadata_types = config.get('skip') or []
    skip_metadata_types = convert_content_to_metadata_type(skip_metadata_types)
    if 'group' in skip_metadata_types:
        _LOG.debug("Skipping 'group' info")
        groups_xml_path = None
    else:
        # If groups_xml_path is specified than used passed in value
        # If no value for groups_xml_path, fallback to whatever is in repomd.xml
        if groups_xml_path is None:
            groups_xml_path = __get_groups_xml_info(repo_dir)
    _LOG.info("Running createrepo with groups file <%s>, this may take a few minutes to complete." % (groups_xml_path))
    start = time.time()
    try:
        set_progress("metadata", metadata_progress_status, progress_callback)
        create_repo(repo_dir, groups=groups_xml_path, checksum_type=checksum_type, skip_metadata_types=skip_metadata_types)
    except CreateRepoError, cre:
        metadata_progress_status = {"state" : "FAILED"}
        set_progress("metadata", metadata_progress_status, progress_callback)
        errors.append(cre)
        return False, errors
    except CancelException, ce:
        metadata_progress_status = {"state" : "CANCELED"}
        set_progress("metadata", metadata_progress_status, progress_callback)
        errors.append(ce)
        return False, errors
    end = time.time()
    _LOG.info("Createrepo finished in %s seconds" % (end - start))
    metadata_progress_status = {"state" : "FINISHED"}
    set_progress("metadata", metadata_progress_status, progress_callback)
    return True, []


def get_repo_checksum_type(publish_conduit, config):
    """
      Lookup checksum type on the repo to use for metadata generation;
      importer sets this value if available on the repo scratchpad.

      @param config: plugin configuration
      @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

      @return checksum_type value
      @rtype str
    """
    checksum_type = config.get('checksum_type')
    if checksum_type:
        return checksum_type
    try:
        scratchpad_data = publish_conduit.get_repo_scratchpad()
        if not scratchpad_data:
            return DEFAULT_CHECKSUM
        checksum_type = scratchpad_data['checksum_type']
    except AttributeError:
        _LOG.debug("get_repo_scratchpad not found on publish conduit")
        checksum_type = DEFAULT_CHECKSUM
    return checksum_type


def __get_groups_xml_info(repo_dir):
    groups_xml_path = None
    repodata_file = os.path.join(repo_dir, "repodata", "repomd.xml")
    repodata_file = encode_unicode(repodata_file)
    if os.path.isfile(repodata_file):
        ftypes = util.get_repomd_filetypes(repodata_file)
        _LOG.debug("repodata has filetypes of %s" % (ftypes))
        if "group" in ftypes:
            comps_ftype = util.get_repomd_filetype_path(
                    repodata_file, "group")
            filetype_path = os.path.join(repo_dir, comps_ftype)
            # createrepo uses filename as mdtype, rename to type.<ext>
            # to avoid filename too long errors
            renamed_filetype_path = os.path.join(os.path.dirname(comps_ftype),
                                     "comps" + '.' + '.'.join(os.path.basename(comps_ftype).split('.')[1:]))
            groups_xml_path = os.path.join(repo_dir, renamed_filetype_path)
            os.rename(filetype_path, groups_xml_path)
    return groups_xml_path


def modify_repo(repodata_dir, new_file, remove=False):
    """
     run modifyrepo to add a new file to repodata directory

     @param repodata_dir: repodata directory path
     @type repodata_dir: string

     @param new_file: new file type to add or remove
     @type new_file: string
    """
    if remove:
        cmd = "modifyrepo --remove %s %s" % (new_file, repodata_dir)
    else:
        cmd = "modifyrepo %s %s" % (new_file, repodata_dir)
    status, out = commands.getstatusoutput(cmd)
    if status != 0:
        _LOG.error("modifyrepo on %s failed" % repodata_dir)
        raise ModifyRepoError(out)
    _LOG.info("modifyrepo with %s on %s finished" % (new_file, repodata_dir))
    return status, out


def _create_repo(dir, groups=None, checksum_type="sha256"):
    if not groups:
        cmd = "createrepo --database --checksum %s --update %s " % (checksum_type, dir)
    else:
        try:
            cmd = "createrepo --database --checksum %s -g %s --update %s " % (checksum_type, groups, dir)
        except UnicodeDecodeError:
            groups = decode_unicode(groups)
            cmd = "createrepo --database --checksum %s -g %s --update %s " % (checksum_type, groups, dir)
    # shlex now can handle unicode strings as well
    cmd = encode_unicode(cmd)
    try:
        cmd = shlex.split(cmd.encode('ascii', 'ignore'))
    except:
        cmd = shlex.split(cmd)

    _LOG.info("started repo metadata update: %s" % (cmd))
    handle = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return handle


def create_repo(dir, groups=None, checksum_type="sha256", skip_metadata_types=[]):
    handle = None
    # Lock the lookup and launch of a new createrepo process
    # Lock is released once createrepo is launched
    if not os.path.exists(dir):
        _LOG.warning("create_repo invoked on a directory which doesn't exist:  %s" % dir)
    CREATE_REPO_PROCESS_LOOKUP_LOCK.acquire()
    try:
        if CREATE_REPO_PROCESS_LOOKUP.has_key(dir):
            raise CreateRepoAlreadyRunningError()
        current_repo_dir = os.path.join(dir, "repodata")
        # Note: backup_repo_dir is used to store presto metadata and possibly other custom metadata types
        # they will be copied back into new 'repodata' if needed.
        backup_repo_dir = None
        current_repo_dir = encode_unicode(current_repo_dir)
        if os.path.exists(current_repo_dir):
            _LOG.info("metadata found; taking backup.")
            backup_repo_dir = os.path.join(dir, "repodata.old")
            if os.path.exists(backup_repo_dir):
                _LOG.debug("clean up any stale dirs")
                shutil.rmtree(backup_repo_dir)
            shutil.copytree(current_repo_dir, backup_repo_dir)
            os.system("chmod -R u+wX %s" % (backup_repo_dir))
        handle = _create_repo(dir, groups=groups, checksum_type=checksum_type)
        if not handle:
            raise CreateRepoError("Unable to execute createrepo on %s" % (dir))
        os.system("chmod -R ug+wX %s" % (dir))
        _LOG.info("Createrepo process with pid %s running on directory %s" % (handle.pid, dir))
        CREATE_REPO_PROCESS_LOOKUP[dir] = handle
    finally:
        CREATE_REPO_PROCESS_LOOKUP_LOCK.release()
    # Ensure we clean up CREATE_REPO_PROCESS_LOOKUP, surround all ops with try/finally
    try:
        # Block on process till complete (Note it may be async terminated)
        out_msg, err_msg = handle.communicate(None)
        if handle.returncode != 0:
            try:
                # Cleanup createrepo's temporary working directory
                cleanup_dir = os.path.join(dir, ".repodata")
                if os.path.exists(cleanup_dir):
                    shutil.rmtree(cleanup_dir)
            except Exception, e:
                _LOG.exception(e)
                _LOG.warn("Unable to remove temporary createrepo dir: %s" % (cleanup_dir))
            if handle.returncode == -9:
                _LOG.warn("createrepo on %s was killed" % (dir))
                raise CancelException()
            else:
                _LOG.error("createrepo on %s failed with returncode <%s>" % (dir, handle.returncode))
                _LOG.error("createrepo stdout:\n%s" % (out_msg))
                _LOG.error("createrepo stderr:\n%s" % (err_msg))
                raise CreateRepoError(err_msg)
        _LOG.info("createrepo on %s finished" % (dir))
        if not backup_repo_dir:
            _LOG.info("Nothing further to check; we got our fresh metadata")
            return
        #check if presto metadata exist in the backup
        repodata_file = os.path.join(backup_repo_dir, "repomd.xml")
        ftypes = util.get_repomd_filetypes(repodata_file)
        base_ftypes = ['primary', 'primary_db', 'filelists_db', 'filelists', 'other', 'other_db', 'group', 'group_gz']
        for ftype in ftypes:
            if ftype in base_ftypes:
                # no need to process these again
                continue
            if ftype in skip_metadata_types and not skip_metadata_types[ftype]:
                _LOG.info("mdtype %s part of skip metadata; skipping" % ftype)
                continue
            filetype_path = os.path.join(backup_repo_dir, os.path.basename(util.get_repomd_filetype_path(repodata_file, ftype)))
            # modifyrepo uses filename as mdtype, rename to type.<ext>
            renamed_filetype_path = os.path.join(os.path.dirname(filetype_path), \
                                         ftype + '.' + '.'.join(os.path.basename(filetype_path).split('.')[1:]))
            os.rename(filetype_path,  renamed_filetype_path)
            if renamed_filetype_path.endswith('.gz'):
                # if file is gzipped, decompress before passing to modifyrepo
                data = gzip.open(renamed_filetype_path).read().decode("utf-8", "replace")
                renamed_filetype_path = '.'.join(renamed_filetype_path.split('.')[:-1])
                open(renamed_filetype_path, 'w').write(data.encode("UTF-8"))
            if os.path.isfile(renamed_filetype_path):
                _LOG.info("Modifying repo for %s metadata" % ftype)
                modify_repo(current_repo_dir, renamed_filetype_path)
    finally:
        if backup_repo_dir:
            shutil.rmtree(backup_repo_dir)
        CREATE_REPO_PROCESS_LOOKUP_LOCK.acquire()
        try:
            del CREATE_REPO_PROCESS_LOOKUP[dir]
        finally:
            CREATE_REPO_PROCESS_LOOKUP_LOCK.release()


def cancel_createrepo(repo_dir):
    """
    Method will lookup a createrepo process associated to 'repo_dir'
    If a createrepo process is running we will send a SIGKILL to it and return True
    Else we return False to denote no process was found
    """
    CREATE_REPO_PROCESS_LOOKUP_LOCK.acquire()
    try:
        if CREATE_REPO_PROCESS_LOOKUP.has_key(repo_dir):
            handle = CREATE_REPO_PROCESS_LOOKUP[repo_dir]
            try:
                os.kill(handle.pid, signal.SIGKILL)
            except Exception, e:
                _LOG.exception(e)
                return False
            return True
        else:
            _LOG.info("No createrepo process found for <%s>" % repo_dir)
            return False
    finally:
        CREATE_REPO_PROCESS_LOOKUP_LOCK.release()


def get_createrepo_pid(repo_dir):
    CREATE_REPO_PROCESS_LOOKUP_LOCK.acquire()
    try:
        if CREATE_REPO_PROCESS_LOOKUP.has_key(repo_dir):
            handle = CREATE_REPO_PROCESS_LOOKUP[repo_dir]
            return handle.pid
        else:
            _LOG.info("No createrepo process found for <%s>" % repo_dir)
            return None
    finally:
        CREATE_REPO_PROCESS_LOOKUP_LOCK.release()


def convert_content_to_metadata_type(content_types_list):
    """
    Convert the unit types to rpm metadata file types
    """
    content_metadata_map = {
        "drpm"         : "prestodelta",
        "errata"       : "updateinfo",
        "packagegroup" : "group",
    }
    if not content_types_list:
        return []
    metadata_type_list = []
    for type in content_types_list:
        if type in content_metadata_map:
            metadata_type_list.append(content_metadata_map[type])
        else:
            metadata_type_list.append(type)
    return metadata_type_list


def get_package_xml(pkg_path):
    """
    Method to generate repo xmls - primary, filelists and other
    for a given rpm.

    @param pkg_path: rpm package path on the filesystem
    @type pkg_path: str

    @return rpm metadata dictionary or empty if rpm path doesnt exist
    @rtype {}
    """
    if not os.path.exists(pkg_path):
        _LOG.info("Package path %s does not exist" % pkg_path)
        return {}
    ts = rpmUtils.transaction.initReadOnlyTransaction()
    po = yumbased.CreateRepoPackage(ts, pkg_path)
    # RHEL6 createrepo throws a ValueError if _cachedir is not set
    po._cachedir = None
    metadata = {'primary' : po.xml_dump_primary_metadata(),
                'filelists': po.xml_dump_filelists_metadata(),
                'other'   : po.xml_dump_other_metadata(),
               }
    return metadata


class YumMetadataGenerator(object):
    """
    Yum metadata generator using per package snippet approach
    """
    def __init__(self, repodir, rpm_units_to_write, checksum_type="sha256",
                 skip_metadata_types=None, is_cancelled=False, group_xml_path=None, updateinfo_xml_path=None, custom_metadata_dict=None):
        """
        @param repodir: repository dir where the repodata directory is created/exists
        @type  repodir: str

        @param rpm_units_to_write: List of rpm units from which repodata is taken and merged
        @type rpm_units_to_write: [AssociatedUnit]

        @param checksum_type: checksum type to use when generating repodata; default is sha256
        @type  checksum_type: str

        @param skip_metadata_types: list of metadata ftypes to skip from the repodata
        @type  skip_metadata_types: []

        @param group_xml_path: path to comps xml to be merged with repodata
        @type group_xml_path: str

        @param updateinfo_xml_path: path to updateinfo xml to be merged with repodata
        @type updateinfo_xml_path: str

        @param custom_metadata_dict: custom metadata from scratchpad
        @param custom_metadata_dict: {}
        """
        self.repodir = repodir
        self.units = rpm_units_to_write
        self.checksum_type = checksum_type
        self.skip = skip_metadata_types or []

        self.primary_xml = None
        self.filelists_xml = None
        self.other_xml = None
        self.backup_repodata_dir = None
        self.is_cancelled=is_cancelled
        self.group_xml_path= group_xml_path
        self.updateinfo_xml_path = updateinfo_xml_path
        self.custom_metadata = custom_metadata_dict or {}
        self.setup_temp_working_dir()
        self.metadata_conf = self.setup_metadata_conf()

    def setup_temp_working_dir(self):
        """
        setup a temporary location where we can do all the work and
        finally merge to final location.
        """
        self.temp_working_dir = os.path.join(self.repodir, ".repodata")
        if not os.path.isdir(self.temp_working_dir):
            os.makedirs(self.temp_working_dir, mode=0755)

    def _backup_existing_repodata(self):
        """
        Takes a backup of any existing repodata files. This is used in the final
        step where other file types in repomd.xml such as presto, updateinfo, comps
        are copied back to the repodata.
        """
        current_repo_dir = os.path.join(self.repodir, "repodata")
        # Note: backup_repo_dir is used to store presto metadata and possibly other custom metadata types
        # they will be copied back into new 'repodata' if needed.
        current_repo_dir = encode_unicode(current_repo_dir)
        if os.path.exists(current_repo_dir):
            _LOG.info("existing metadata found; taking backup.")
            self.backup_repodata_dir = os.path.join(self.repodir, "repodata.old")
            if os.path.exists(self.backup_repodata_dir):
                _LOG.debug("clean up any stale dirs")
                shutil.rmtree(self.backup_repodata_dir)
            shutil.copytree(current_repo_dir, self.backup_repodata_dir)
            os.system("chmod -R u+wX %s" % self.backup_repodata_dir)

    def setup_metadata_conf(self):
        """
        Sets up the yum metadata config to perform the sqlitedb and repomd.xml generation.
        """
        conf = MetaDataConfig()
        conf.directory = self.repodir
        conf.database = 1
        conf.verbose = 1
        conf.skip_stat = 1
        conf.sumtype = self.checksum_type
        return conf

    def init_primary_xml(self):
        """
        Initialize the primary xml file where metadata snippets are written
        """
        filename = os.path.join(self.temp_working_dir, "primary.xml.gz")
        self.primary_xml= GzipFile(filename, 'w', compresslevel=9)
        self.primary_xml.write("""<?xml version="1.0" encoding="UTF-8"?>\n <metadata xmlns="http://linux.duke.edu/metadata/common"
xmlns:rpm="http://linux.duke.edu/metadata/rpm" packages="%s"> \n""" % len(self.units))

    def init_filelists_xml(self):
        """
        Initialize the filelists xml file where metadata snippets are written
        """
        filename = os.path.join(self.temp_working_dir, "filelists.xml.gz")
        self.filelists_xml= GzipFile(filename, 'w', compresslevel=9)
        self.filelists_xml.write("""<?xml version="1.0" encoding="UTF-8"?>
<filelists xmlns="http://linux.duke.edu/metadata/filelists" packages="%s"> \n""" % len(self.units))

    def init_other_xml(self):
        """
        Initialize the other xml file where metadata snippets are written
        """
        filename = os.path.join(self.temp_working_dir, "other.xml.gz")
        self.other_xml= GzipFile(filename, 'w', compresslevel=9)
        self.other_xml.write("""<?xml version="1.0" encoding="UTF-8"?>
<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="%s"> \n""" % len(self.units))

    def close_primary_xml(self):
        """
        All the data should be written at this point; invoke this to
        close the primary xml gzipped file
        """
        self.primary_xml.write("""\n </metadata>""")
        self.primary_xml.close()

    def close_filelists_xml(self):
        """
        All the data should be written at this point; invoke this to
        close the filelists xml gzipped file
        """
        self.filelists_xml.write("""\n </filelists>""")
        self.filelists_xml.close()

    def close_other_xml(self):
        """
        All the data should be written at this point; invoke this to
        close the other xml gzipped file
        """
        self.other_xml.write("""\n </otherdata>""")
        self.other_xml.close()

    def merge_unit_metadata(self):
        """
        This performs the actual merge of the snippets. The xml files are initialized and
        each unit metadata is written to the xml files. These units here should be rpm
        units. If a unit doesnt have repodata info, log the message and skip that unit.
        Finally the gzipped xmls are closed when all the units are written.
        """
        _LOG.info("Performing per unit metadata merge on %s units" % len(self.units))
        start = time.time()
        self.init_primary_xml()
        self.init_filelists_xml()
        self.init_other_xml()
        try:
            for unit in self.units:
                if self.is_cancelled:
                    _LOG.warn("cancelling merge unit metadata")
                    raise CancelException()
                if unit.metadata.has_key('repodata'):
                    try:
                        self.primary_xml.write(unit.metadata['repodata']['primary'].encode('utf-8'))
                        self.filelists_xml.write(unit.metadata['repodata']['filelists'].encode('utf-8'))
                        self.other_xml.write(unit.metadata['repodata']['other'].encode('utf-8'))
                    except Exception, e:
                        _LOG.error("Error occurred writing metadata to file; Exception: %s" % e)
                        continue
                else:
                    _LOG.debug("No repodata found for the unit; continue")
                    continue
        finally:
            self.close_primary_xml()
            self.close_filelists_xml()
            self.close_other_xml()
            end = time.time()
        _LOG.info("per unit metadata merge completed in %s seconds" % (end - start))

    def merge_custom_repodata(self):
        """
        merge any repodata preserved on the repo scratchpad
        """
        _LOG.info("check scratchpad for any repodata")
        if not self.custom_metadata:
            # nothing found on scratchpad
            return False
        current_repo_dir = os.path.join(self.repodir, "repodata")

        for ftype, fxml in self.custom_metadata.items():
            if not fxml:
                continue
            ftype_xml_path = os.path.join(self.repodir, "%s.xml" % ftype)
            f = open(ftype_xml_path, "w")
            try:
                data = fxml.encode('utf-8')
                f.write(data)
            except Exception, e:
                _LOG.exception("Unable to write file type %s" % ftype)
                continue
            finally:
                f.close()
            # merge the xml we just wrote with repodata
            if os.path.isfile(ftype_xml_path):
                _LOG.info("Modifying repo for %s metadata" % ftype)
                modify_repo(current_repo_dir, ftype_xml_path)
        return True

    def merge_comps_xml(self):
        """
        merge comps xml file to repodata
        """
        if self.group_xml_path is None or not os.path.isfile(self.group_xml_path):
            # no group xml formed nothing to do
            _LOG.info("comps xml path does not exist; skipping merge")
            return
        repodata_working_dir = os.path.join(self.repodir, "repodata")
        _LOG.info("Modifying repo for %s metadata" % "comps")
        modify_repo(repodata_working_dir, self.group_xml_path)

    def merge_updateinfo_xml(self):
        """
        merge updateinfo xml file to repodata
        """
        if self.updateinfo_xml_path is None or not os.path.isfile(self.updateinfo_xml_path):
            # no updateinfo xml formed, nothing to do
            _LOG.info("updateinfo xml path does not exist; skipping merge")
            return
        repodata_working_dir = os.path.join(self.repodir, "repodata")
        _LOG.info("Modifying repo for %s metadata" % "updateinfo")
        modify_repo(repodata_working_dir, self.updateinfo_xml_path)

    def merge_other_filetypes_from_backup(self):
        """
        Merges any other filetypes in the backed up repodata that needs to be included
        back into the repodata. This is where the presto, updateinfo and comps xmls are
        looked up in old repomd.xml and merged back to the new using modifyrepo.
        primary, filelists and other xmls are excluded from the process.
        """
        _LOG.info("Performing merge on other file types")
        try:
            if not self.backup_repodata_dir:
                _LOG.info("Nothing further to check; we got our fresh metadata")
                return
            current_repo_dir = os.path.join(self.repodir, "repodata")
            #check if presto metadata exist in the backup
            repodata_file = os.path.join(self.backup_repodata_dir, "repomd.xml")
            ftypes = util.get_repomd_filetypes(repodata_file)
            base_ftypes = ['primary', 'primary_db', 'filelists_db', 'filelists', 'other', 'other_db']
            for ftype in ftypes:
                if self.is_cancelled:
                    _LOG.warn("cancel merge other filetype metadata")
                    raise CancelException()
                if ftype in base_ftypes:
                    # no need to process these again
                    continue
                if ftype in self.skip and not self.skip[ftype]:
                    _LOG.info("mdtype %s part of skip metadata; skipping" % ftype)
                    continue
                filetype_path = os.path.join(self.backup_repodata_dir, os.path.basename(util.get_repomd_filetype_path(repodata_file, ftype)))
                # modifyrepo uses filename as mdtype, rename to type.<ext>
                renamed_filetype_path = os.path.join(os.path.dirname(filetype_path),\
                    ftype + '.' + '.'.join(os.path.basename(filetype_path).split('.')[1:]))
                os.rename(filetype_path,  renamed_filetype_path)
                if renamed_filetype_path.endswith('.gz'):
                    # if file is gzipped, decompress before passing to modifyrepo
                    data = gzip.open(renamed_filetype_path).read().decode("utf-8", "replace")
                    renamed_filetype_path = '.'.join(renamed_filetype_path.split('.')[:-1])
                    open(renamed_filetype_path, 'w').write(data.encode("UTF-8"))
                if os.path.isfile(renamed_filetype_path):
                    _LOG.info("Modifying repo for %s metadata" % ftype)
                    modify_repo(current_repo_dir, renamed_filetype_path)
        finally:
            if self.backup_repodata_dir:
                shutil.rmtree(self.backup_repodata_dir)

    def run(self):
        """
        Invokes the metadata generation by taking a backup of existing repodata;
        looking up units and merging the per unit snippets; generate sqlite db,
        repomd files using createrepo apis and finally merge back any other
        """
        # backup existing repodata dir
        self._backup_existing_repodata()
        # extract the per rpm unit metadata and merge to create package xml data
        self.merge_unit_metadata()
        # setup the yum config to do the final steps of generating sqlite db files
        mdgen = MetaDataGenerator(self.metadata_conf)
        mdgen.doRepoMetadata()
        # do the final move to the repodata location from .repodata
        mdgen.doFinalMove()
        # lookup and merge updateinfo, comps and other metadata
        self.merge_comps_xml()
        self.merge_updateinfo_xml()
        # merge any custom metadata stored on the scratchpad, this includes prestodelta
        self.merge_custom_repodata()


def generate_yum_metadata(repo_dir, units_to_write, config, progress_callback=None,
                          is_cancelled=False, group_xml_path=None, updateinfo_xml_path=None, repo_scratchpad=None):
    """
      build all the necessary info and invoke createrepo to generate metadata

      @param repo_dir: repository dir where the repodata directory is created/exists
      @type  repo_dir: str

      @param units_to_write: List of rpm units from which repodata is taken and merged
      @type units_to_write: [AssociatedUnit]

      @param config: plugin configuration
      @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

      @param progress_callback: callback to report progress info to publish_conduit
      @type  progress_callback: function

      @param group_xml_path: path to the package groups/package category comps info
      @type group_xml_path: str

      @param updateinfo_xml_path: path to updateinfo xml to be merged with repodata
      @type updateinfo_xml_path: str

      @param repo_scratchpad: repository scratchpad to lookup custom metadata or checksum type info if any
      @param repo_scratchpad: {}

      @return True on success, False on error and list of errors
      @rtype bool, []
    """
    errors = []
    metadata_progress_status = {"state" : "IN_PROGRESS"}
    skip_metadata_types = config.get('skip') or []
    skip_metadata_types = convert_content_to_metadata_type(skip_metadata_types)
    checksum_type = repo_scratchpad.get('checksum_type', DEFAULT_CHECKSUM)
    custom_metadata = {}
    if repo_scratchpad.has_key("repodata"):
        custom_metadata = repo_scratchpad["repodata"]
    start = time.time()
    try:
        set_progress("metadata", metadata_progress_status, progress_callback)
        create_yum_metadata = YumMetadataGenerator(repo_dir, units_to_write, checksum_type=checksum_type,
            skip_metadata_types=skip_metadata_types, is_cancelled=is_cancelled, group_xml_path=group_xml_path,
            updateinfo_xml_path=updateinfo_xml_path, custom_metadata_dict=custom_metadata)
        create_yum_metadata.run()
    except CancelException, ce:
        metadata_progress_status = {"state" : "CANCELED"}
        set_progress("metadata", metadata_progress_status, progress_callback)
        errors.append(ce)
        return False, errors
    except Exception, e:
        metadata_progress_status = {"state" : "FAILED"}
        set_progress("metadata", metadata_progress_status, progress_callback)
        errors.append(e)
        return False, errors
    end = time.time()
    _LOG.info("Metadata generation finished in %s seconds" % (end - start))
    metadata_progress_status = {"state" : "FINISHED"}
    set_progress("metadata", metadata_progress_status, progress_callback)
    return True, []

