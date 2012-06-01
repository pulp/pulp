# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
import logging
import os
import shlex
import shutil
import subprocess
import threading
import signal
import time
from pulp.yum_plugin import util
from pulp.common.util import encode_unicode, decode_unicode

log = logging.getLogger(__name__)
__yum_lock = threading.Lock()

# In memory lookup table for createrepo processes
# Responsible for 2 tasks.  1) Restrict only one createrepo per repo_dir, 2) Allow an async cancel of running createrepo
CREATE_REPO_PROCESS_LOOKUP = {}
CREATE_REPO_PROCESS_LOOKUP_LOCK = threading.Lock()

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

def generate_metadata(repo, publish_conduit, config, progress_callback=None):
    """
      build all the necessary info and invoke createrepo to generate metadata

      @param repo: metadata describing the repository
      @type  repo: L{pulp.server.content.plugins.data.Repository}

      @param config: plugin configuration
      @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

      @param progress_callback: callback to report progress info to publish_conduit
      @type  progress_callback: function

      @return True on success, False on error
      @rtype bool
    """
    errors = []
    if not config.get('generate_metadata'):
        metadata_progress_status = {"state" : "SKIPPED"}
        set_progress("metadata", metadata_progress_status, progress_callback)
        log.info('skip metadata generation for repo %s' % repo.id)
        return False, []
    metadata_progress_status = {"state" : "IN_PROGRESS"}
    repo_dir = repo.working_dir
    checksum_type = get_repo_checksum_type(repo, publish_conduit, config)
    metadata_types = config.get('skip_content_types') or {}
    metadata_types = convert_content_to_metadata_type(metadata_types)
    if 'group' not in metadata_types:
        groups_xml_path = None
    else:
        groups_xml_path = __get_groups_xml_info(repo_dir)
    log.info("Running createrepo, this may take a few minutes to complete.")
    start = time.time()
    try:
        set_progress("metadata", metadata_progress_status, progress_callback)
        create_repo(repo_dir, groups=groups_xml_path, checksum_type=checksum_type, metadata_types=metadata_types)
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
    log.info("Createrepo finished in %s seconds" % (end - start))
    metadata_progress_status = {"state" : "FINISHED"}
    set_progress("metadata", metadata_progress_status, progress_callback)
    return True, []

def get_repo_checksum_type(repo, publish_conduit, config):
    """
      Lookup checksum type on the repo to use for metadata generation;
      importer sets this value if available on the repo scratchpad.

      @param repo: metadata describing the repository
      @type  repo: L{pulp.server.content.plugins.data.Repository}

      @param config: plugin configuration
      @type  config: L{pulp.server.content.plugins.config.PluginCallConfiguration}

      @return checksum_type value
      @rtype str
    """
    DEFAULT_CHECKSUM = "sha256"
    checksum_type = config.get('checksum_type')
    print checksum_type
    if checksum_type:
        return checksum_type
    scratchpad_data = publish_conduit.get_repo_scratchpad()
    if not scratchpad_data:
        return DEFAULT_CHECKSUM
    checksum_type = scratchpad_data['checksum_type']
    return checksum_type


def __get_groups_xml_info(repo_dir):
    groups_xml_path = None
    repodata_file = os.path.join(repo_dir, "repodata", "repomd.xml")
    repodata_file = encode_unicode(repodata_file)
    if os.path.isfile(repodata_file):
        ftypes = util.get_repomd_filetypes(repodata_file)
        log.debug("repodata has filetypes of %s" % (ftypes))
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
        log.error("modifyrepo on %s failed" % repodata_dir)
        raise ModifyRepoError(out)
    log.info("modifyrepo with %s on %s finished" % (new_file, repodata_dir))
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

    log.info("started repo metadata update: %s" % (cmd))
    handle = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return handle

def create_repo(dir, groups=None, checksum_type="sha256", metadata_types=[]):
    handle = None
    # Lock the lookup and launch of a new createrepo process
    # Lock is released once createrepo is launched
    if not os.path.exists(dir):
        log.warning("create_repo invoked on a directory which doesn't exist:  %s" % dir)
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
            log.info("metadata found; taking backup.")
            backup_repo_dir = os.path.join(dir, "repodata.old")
            if os.path.exists(backup_repo_dir):
                log.debug("clean up any stale dirs")
                shutil.rmtree(backup_repo_dir)
            shutil.copytree(current_repo_dir, backup_repo_dir)
            os.system("chmod -R u+wX %s" % (backup_repo_dir))
        handle = _create_repo(dir, groups=groups, checksum_type=checksum_type)
        if not handle:
            raise CreateRepoError("Unable to execute createrepo on %s" % (dir))
        os.system("chmod -R ug+wX %s" % (dir))
        log.info("Createrepo process with pid %s running on directory %s" % (handle.pid, dir))
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
                log.warn(e)
                log.warn("Unable to remove temporary createrepo dir: %s" % (cleanup_dir))
            if handle.returncode == -9:
                log.warn("createrepo on %s was killed" % (dir))
                raise CancelException()
            else:
                log.error("createrepo on %s failed with returncode <%s>" % (dir, handle.returncode))
                log.error("createrepo stdout:\n%s" % (out_msg))
                log.error("createrepo stderr:\n%s" % (err_msg))
                raise CreateRepoError(err_msg)
        log.info("createrepo on %s finished" % (dir))
        if not backup_repo_dir:
            log.info("Nothing further to check; we got our fresh metadata")
            return
        #check if presto metadata exist in the backup
        repodata_file = os.path.join(backup_repo_dir, "repomd.xml")
        ftypes = util.get_repomd_filetypes(repodata_file)
        base_ftypes = ['primary', 'primary_db', 'filelists_db', 'filelists', 'other', 'other_db', 'group', 'group_gz']
        for ftype in ftypes:
            if ftype in base_ftypes:
                # no need to process these again
                continue
            if ftype in metadata_types and not metadata_types[ftype]:
                log.info("mdtype %s part of skip metadata; skipping" % ftype)
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
                log.info("Modifying repo for %s metadata" % ftype)
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
                log.info(e)
                return False
            return True
        else:
            log.info("No createrepo process found for <%s>" % repo_dir)
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
            log.info("No createrepo process found for <%s>" % repo_dir)
            return None
    finally:
        CREATE_REPO_PROCESS_LOOKUP_LOCK.release()

def convert_content_to_metadata_type(content_types_list):
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