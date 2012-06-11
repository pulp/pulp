# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
from datetime import datetime

import os
import logging
import sys
import time
import traceback
from gettext import gettext as _
from StringIO import StringIO

from pulp.common import dateutils
from pulp.server import comps_util, config, async
from pulp.server.api.errata import ErrataApi, ErrataHasReferences
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.distribution import DistributionApi
from pulp.server.api.synchronizers import BaseSynchronizer, YumSynchronizer, \
    yum_rhn_progress_callback, local_progress_callback, FileSynchronizer
from pulp.server.api.repo_sync_task import RepoSyncTask
from pulp.server.api.repo_clone_task import RepoCloneTask
from pulp.server.auditing import audit
from pulp.server.async import run_async
from pulp.server.event.handler.task import TaskDequeued
from pulp.server.exceptions import PulpException
from pulp.server.tasking.exception import CancelException
from pulp.server.tasking.exception import ConflictingOperationException
from pulp.server.util import top_repos_location, top_gpg_location, encode_unicode
log = logging.getLogger(__name__)

repo_api = RepoApi()
package_api = PackageApi()
errata_api = ErrataApi()
distro_api = DistributionApi()

# synchronization type map ----------------------------------------------------
type_classes = {
    'yum': YumSynchronizer,
    'file' : FileSynchronizer,
}

@audit()
def clone(id, clone_id, clone_name, feed='parent', groupid=[], relative_path=None,
        progress_callback=None, timeout=None, filters=[], publish=None):
    """
    Run a repo clone asynchronously.
    @rtype pulp.server.tasking.task or None
    @return on success a task object is returned
            on failure None is returned
    @return
    """
    repo_api.check_for_whitespace(clone_id, "clone_id")
    if relative_path:
        repo_api.check_for_whitespace(relative_path, "relative_path")
    repo = repo_api.repository(id)
    if repo is None:
        raise PulpException("A Repo with id %s does not exist" % id)
    cloned_repo = repo_api.repository(clone_id)
    if cloned_repo is not None:
        raise PulpException("A Repo with id %s exists. Choose a different id." % clone_id)

    REPOS_LOCATION = top_repos_location()
    parent_feed = "file://" + REPOS_LOCATION + "/" + repo["relative_path"]
    feed_cert_data = {}
    consumer_cert_data = {}

    # Utility function to save space making sure files are closed after reading
    def read_cert_file(filename):
        filename = encode_unicode(filename)
        f = open(filename, 'r')
        contents = f.read()
        f.close()
        return contents

    if repo['feed_ca'] and repo['feed_cert']:
        feed_cert_data = {'ca' : read_cert_file(repo['feed_ca']),
                        'cert' : read_cert_file(repo['feed_cert'])}

    if repo['consumer_ca'] and repo['consumer_cert']:
        consumer_cert_data = {'ca' : read_cert_file(repo['consumer_ca']),
                        'cert' : read_cert_file(repo['consumer_cert'])}

    if relative_path is None:
        relative_path = clone_id
    # inherit content types from parent
    content_types = repo['content_types']
    log.info("Creating [%s] feed repo [%s] cloned from [%s] with relative_path [%s]" % (feed, clone_id, id, relative_path))
    repo_api.create(clone_id, clone_name, repo['arch'], feed=parent_feed, groupid=groupid,
                    relative_path=relative_path, feed_cert_data=feed_cert_data,
                    consumer_cert_data=consumer_cert_data, checksum_type=repo['checksum_type'], 
                    content_types=content_types, publish=publish)

    # Associate filters if specified
    if len(filters) > 0:
        repo_api.add_filters(clone_id, filter_ids=filters)
        encoded_filters = [encode_unicode(f) for f in filters]
    else:
        encoded_filters = []

    task = RepoCloneTask(_clone,
                         [clone_id],
                         {'id':id,
                          'clone_name':clone_name,
                          'feed':feed,
                          'relative_path':relative_path,
                          'groupid':groupid,
                          'filters':encoded_filters},
                         timeout=timeout)
    if feed in ('feedless', 'parent'):
        task.set_progress('progress_callback', local_progress_callback)
    else:
        task.set_progress('progress_callback', yum_rhn_progress_callback)
    content_type = repo['content_types']
    synchronizer = get_synchronizer(content_type)
    # enable synchronizer as a clone process
    synchronizer.set_clone(id)
    task.set_synchronizer(synchronizer)
    if content_type == 'yum':
        task.weight = config.config.getint('yum', 'task_weight')
    task = async.enqueue(task)
    if task is None:
        log.error("Unable to create repo._clone task for [%s]" % (id))
    return task


def _clone(clone_id, id, clone_name, feed='parent', relative_path=None, groupid=None,
            filters=(), progress_callback=None, synchronizer=None):
    repo = repo_api.repository(id)

    # Sync from parent repo
    try:
        _sync(clone_id, progress_callback=progress_callback, synchronizer=synchronizer)
    except CancelException, e:
        log.info(_('Content sync canceled'))
        raise
    except Exception, e:
        log.error(e)
        log.warn("Traceback: %s" % (traceback.format_exc()))
        raise

    # Update feed type for cloned repo if "origin" or "feedless"
    cloned_repo = repo_api.repository(clone_id)
    if feed == "origin":
        cloned_repo['source'] = repo['source']
    elif feed == "none":
        cloned_repo['source'] = None
    repo_api.collection.save(cloned_repo, safe=True)

    # Update clone_ids for parent repo
    clone_ids = repo['clone_ids']
    clone_ids.append(clone_id)
    repo['clone_ids'] = clone_ids
    repo_api.collection.save(repo, safe=True)

    # Update repoids on distributions
    for distro_id in cloned_repo["distributionid"]:
        distro = distro_api.distribution(distro_id)
        distro["repoids"].append(clone_id)
        distro_api.collection.save(distro, safe=True)

    # Update gpg keys from parent repo
    keylist = []
    key_paths = repo_api.listkeys(id)
    for key_path in key_paths:
        key_path = os.path.join(top_gpg_location(), key_path)
        f = open(key_path)
        fn = os.path.basename(key_path)
        content = f.read()
        keylist.append((fn, content))
        f.close()
    repo_api.addkeys(clone_id, keylist)

    # Add files to cloned repo
    repo_api.add_file(repoid=clone_id, fileids=repo["files"])


@audit()
def sync(repo_id, timeout=None, skip=None, max_speed=None, threads=None):
    """
    Run a repo sync asynchronously.
    @rtype pulp.server.tasking.task or None
    @return on success a task object is returned
            on failure None is returned
    @return
    """
    repo = repo_api.repository(repo_id)
    task = RepoSyncTask(_sync,
                        [repo_id],
                        {'skip':skip,
                         'max_speed':max_speed,
                         'threads':threads},
                        timeout=timeout)
    if repo['source'] is not None:
        source_type = repo['source']['type']
        if source_type in ('remote'):
            # its a remote sync, use supported content types to select synchronizer
            task.set_progress('progress_callback', yum_rhn_progress_callback)
        elif source_type in ('local'):
            task.set_progress('progress_callback', local_progress_callback)
        content_type = repo['content_types']
        synchronizer = get_synchronizer(content_type)
        task.set_synchronizer(synchronizer)
        if content_type == 'yum':
            task.weight = config.config.getint('yum', 'task_weight')
    task.add_dequeue_hook(TaskDequeued())
    task = async.enqueue(task)
    if task is None:
        log.error("Unable to create repo._sync task for [%s]" % (repo_id))
    return task

def get_synchronizer(source_type):
    '''
    Returns an instance of a Synchronizer object which can be used for
    repository synchronization

    @param source_type: repository source type
    @type source_type: string

    Returns an instance of a pulp.server.api.repo_sync.BaseSynchronizer object
    '''
    if source_type not in type_classes:
        raise PulpException('Could not find synchronizer for repo type [%s]', source_type)
    synchronizer = type_classes[source_type]()
    return synchronizer


def _sync(repo_id, skip=None, progress_callback=None, synchronizer=None,
          max_speed=None, threads=None):
    """
    Sync a repo from the URL contained in the feed
    @param repo_id repository id
    @type repo_id string
    @param skip_dict dictionary of item types to skip from synchronization
    @type skip_dict dict
    @param progress_callback callback to display progress of synchronization
    @type progress_callback method
    @param synchronizer instance of a specific synchronizer class
    @type synchronizer instance of a L{pulp.server.api.repo_sync.BaseSynchronizer}
    @param max_speed maximum download bandwidth in KB/sec per thread for yum downloads
    @type max_speed int
    @param threads maximum number of threads to use for yum downloading
    @type threads int
    """
    if not repo_api.set_sync_in_progress(repo_id, True):
        log.error("We saw sync was in progress for [%s]" % (repo_id))
        raise ConflictingOperationException(_('Sync for repo [%s] already in progress') % repo_id)

    try:
        log.info("Sync invoked for repo <%s>" % (repo_id))
        if not skip:
            skip = {}
        repo = repo_api._get_existing_repo(repo_id)
        repo_source = repo['source']
        if not repo_source:
            raise PulpException("This repo is not setup for sync. Please add packages using upload.")
        if not synchronizer:
            if repo['content_types'] in ('yum'):
                source = repo['content_types']
            elif repo['content_types'] in ('file'):
                source = repo['content_types']
            synchronizer = get_synchronizer(source)
            synchronizer.set_callback(progress_callback)
        log.info("Sync of %s starting, skip_dict = %s" % (repo_id, skip))
        start_sync_items = time.time()

        sync_packages, sync_errataids = fetch_content(repo["id"], repo_source, skip,
            progress_callback, synchronizer, max_speed, threads)
        end_sync_items = time.time()
        log.info("Sync on %s returned %s packages, %s errata in %s seconds" % (repo_id, len(sync_packages),
            len(sync_errataids), (end_sync_items - start_sync_items)))
        # We need to update the repo object in Mongo to account for
        # package_group info added in sync call
        repo = repo_api._get_existing_repo(repo_id)
        if not skip.has_key('packages') or skip['packages'] != 1:
            old_pkgs = list(set(repo["packages"]).difference(set(sync_packages.keys())))
            old_pkgs = map(package_api.package, old_pkgs)
            old_pkgs = filter(lambda pkg: pkg["repo_defined"], old_pkgs)
            new_pkgs = list(set(sync_packages.keys()).difference(set(repo["packages"])))
            new_pkgs = map(lambda pkg_id: sync_packages[pkg_id], new_pkgs)
            log.info("%s old packages to process, %s new packages to process" % \
                (len(old_pkgs), len(new_pkgs)))
            synchronizer.progress_callback(step="Removing %s packages" % (len(old_pkgs)))
            # Remove packages that are no longer in source repo
            repo_api.remove_packages(repo["id"], old_pkgs)
            # Refresh repo object since we may have deleted some packages
            repo = repo_api._get_existing_repo(repo_id)
            synchronizer.progress_callback(step="Adding %s new packages" % (len(new_pkgs)))
            for pkg in new_pkgs:
                repo_api._add_package(repo, pkg)
            # Update repo for package additions
            repo_api.collection.save(repo, safe=True)

        if not skip.has_key('errata') or skip['errata'] != 1:
            # Determine removed errata
            synchronizer.progress_callback(step="Processing Errata")
            log.info("Examining %s errata from repo %s" % (len(repo_api.errata(repo_id)), repo_id))
            repo_errata = [e['id'] for e in repo_api.errata(repo_id)]
            old_errata = list(set(repo_errata).difference(set(sync_errataids)))
            new_errata = list(set(sync_errataids).difference(set(repo_errata)))
            log.info("Removing %s old errata from repo %s" % (len(old_errata), repo_id))
            repo_api.delete_errata(repo_id, old_errata)
            for eid in old_errata:
                try:
                    errata_api.delete(eid)
                except ErrataHasReferences:
                    log.info('errata "%s" has references, not deleted',eid)
            # Refresh repo object
            repo = repo_api._get_existing_repo(repo_id) #repo object must be refreshed
            log.info("Adding %s new errata to repo %s" % (len(new_errata), repo_id))
            for eid in new_errata:
                repo_api._add_erratum(repo, eid)
            repo_api.collection.save(repo, safe=True)
        now = datetime.now(dateutils.local_tz())
        repo_api.collection.update({"id":repo_id},
                                   {"$set":{"last_sync":dateutils.format_iso8601_datetime(now)}})

        # Throw cancel exception when sync is canceled during package and errata removal
        if synchronizer.stopped:
            raise CancelException()

        synchronizer.progress_callback(step="Finished")
        return True
    finally:
        repo_api.set_sync_in_progress(repo_id, False)


def fetch_content(repo_id, repo_source, skip_dict={}, progress_callback=None, synchronizer=None,
        max_speed=None, threads=None):
    '''
    Synchronizes content for the given RepoSource.

    @param repo_id: ID of repo to synchronize; may not be None
    @type  repo: str
    @param repo_source: indicates the source from which the repo data will be syncced; may not be None
    @type  repo_source: L{pulp.model.RepoSource}
    @param skip_dict: Will skip synching this type of data
    @type skip_dict: dictionary with possible values of: packages, errata, distribution
    @param progress_callback: call back to display progress of sync operation
    @type progress_callback:
    @param synchronizer: instace of a synchronizer to use for synching
    @type synchronizer: L{pulp.server.api.repo_sync.BaseSynchronizer}
    @param max_speed: Limit download speed in KB/sec, not applicable to Local Syncs
    @type max_speed: int
    @param threads: number of threads to use for content downloads
    @type threads: int
    '''
    if not synchronizer:
        synchronizer = get_synchronizer(repo_source['type'])
    repo_dir = synchronizer.sync(repo_id, repo_source, skip_dict,
            progress_callback, max_speed, threads)
    if progress_callback is not None:
        synchronizer.progress['step'] = "Importing data into pulp"
        progress_callback(synchronizer.progress)
    # Process Packages
    added_packages = synchronizer.process_packages_from_source(repo_dir, repo_id, skip_dict, progress_callback)
    # Process Distribution
    synchronizer.add_distribution_from_dir(repo_dir, repo_id, skip_dict)
    # Process Files
    synchronizer.add_files_from_dir(repo_dir, repo_id, skip_dict)
    # Process Metadata
    added_errataids = synchronizer.import_metadata(repo_dir, repo_id, skip_dict)
    return added_packages, added_errataids


def import_comps(repoid, comps_data=None):
    """
    Creates packagegroups and categories from a comps.xml file
    @param repoid: repository Id
    @param compsfile: comps xml stream
    @return: True if success; else False
    """
    repo = repo_api._get_existing_repo(repoid)
    compsobj = StringIO()
    compsobj.write(comps_data.encode("utf8"))
    compsobj.seek(0, 0)
    bs = BaseSynchronizer()
    status = bs.sync_groups_data(compsobj, repo)
    repo_api.collection.save(repo, safe=True)
    # write the xml to repodata location
    repo_api._update_groups_metadata(repoid)
    return status

def export_comps(repoid):
    """
    Creates packagegroups and categories from a comps.xml file
    @param compsfile: comps xml stream
    @return: comps xml stream
    """
    repo = repo_api._get_existing_repo(repoid)
    xml = comps_util.form_comps_xml(repo['packagegroupcategories'],
                repo['packagegroups'])
    return xml
