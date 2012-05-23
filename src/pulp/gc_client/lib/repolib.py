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

'''
Logic methods for handling repo bind, unbind, and update operations. This module
is independent of how the requests for these operations are received. In other words,
this module does not care if the required information for these commands is received
through API calls or the message bus. The logic is still the same and occurs
entirely on the consumer.
'''

# Python
import os
import shutil

# Pulp
from logging import getLogger
from pulp.gc_client.lib.lock import Lock
from pulp.gc_client.lib.repo_file import Repo, RepoFile, MirrorListFile, RepoKeyFiles, CertFiles
from pulp.common.util import encode_unicode, decode_unicode

log = getLogger(__name__)

# -- public ----------------------------------------------------------------

def bind(repo_filename, 
         mirror_list_filename,
         keys_root_dir,
         cert_root_dir,
         repo_id,
         repo_data,
         url_list,
         gpg_keys,
         cacert,
         clientcert,
         enabled,
         lock=None):
    '''
    Uses the given data to safely bind a repo to a repo file. This call will
    determine the best method for representing the repo given the data in the
    repo object as well as the list of URLs where the repo can be found.

    The default lock is defined at the module level and is
    used to ensure that concurrent access to the give files is prevented. Specific
    locks can be passed in for testing purposes to circumvent the default
    location of the lock which requires root access.

    @param repo_filename: full path to the location of the repo file in which
                          the repo will be bound; this file does not need to
                          exist prior to this call
    @type  repo_filename: string

    @param mirror_list_filename: full path to the location of the mirror list file
                                 that should be written for the given repo if
                                 necessary; this should be unique for the given repo
    @type  mirror_list_filename: string

    @param keys_root_dir: absolute path to the root directory in which the keys for
                          all repos will be stored
    @type  keys_root_dir: string
    
    @param cert_root_dir: absolute path to the root directory in which the certs for
                          all repos will be stored
    @type  cert_root_dir: string

    @param repo_id: uniquely identifies the repo being updated
    @type  repo_id: string

    @param repo_data: contains data on the repo being bound
    @type  repo_data: dict {string: string}

    @param url_list: list of URLs that will be used to access the repo; this call
                     will determine the best way to represent the URL list in
                     the repo definition
    @type  url_list: list of strings

    @param gpg_keys: mapping of key name to contents for GPG keys to be used when
                     verifying packages from this repo
    @type  gpg_keys: dict {string: string}
    
    @param cacert: The CA certificate (PEM).
    @type cacert: str
    
    @param clientcert: The client certificate (PEM).
    @type clientcert: str

    @param lock: if the default lock is unacceptble, it may be overridden in this variable
    @type  lock: L{Lock}
    '''

    if not lock:
        lock = Lock('/var/run/subsys/pulp/repolib.pid')

    lock.acquire()
    try:
        log.info('Binding repo [%s]' % repo_id)

        repo_file = RepoFile(repo_filename)
        repo_file.load()

        # In the case of an update, only the changed values will have been sent.
        # Therefore, any of the major data components (repo data, url list, keys)
        # may be None.

        if repo_data is not None:
            repo = _convert_repo(repo_id, enabled, repo_data['display_name'])
        else:
            repo = repo_file.get_repo(repo_id)

        if gpg_keys is not None:
            _handle_gpg_keys(repo, gpg_keys, keys_root_dir)

        _handle_certs(repo, cert_root_dir, cacert, clientcert)

        if url_list is not None:
            _handle_host_urls(repo, url_list, mirror_list_filename)

        if repo_file.get_repo(repo.id):
            log.info('Updating existing repo [%s]' % repo.id)
            repo_file.update_repo(repo)
        else:
            log.info('Adding new repo [%s]' % repo.id)
            repo_file.add_repo(repo)
            
        repo_file.save()
    finally:
        lock.release()

def unbind(repo_filename, mirror_list_filename, keys_root_dir, cert_root_dir, repo_id, lock=None):
    '''
    Removes the repo identified by repo_id from the given repo file. If the repo is
    not bound, this call has no effect. If the mirror list file exists, it will be
    deleted.

    The default lock is defined at the module level and is
    used to ensure that concurrent access to the give files is prevented. Specific
    locks can be passed in for testing purposes to circumvent the default
    location of the lock which requires root access.

    @param repo_filename: full path to the location of the repo file in which
                          the repo will be removed; if this file does not exist
                          this call has no effect
    @type  repo_filename: string

    @param mirror_list_filename: full path to the location of the mirror list file
                                 that may exist for the given repo; if the file does
                                 not exist this field will be ignored
    @type  mirror_list_filename: string

    @param keys_root_dir: absolute path to the root directory in which the keys for
                          all repos will be stored
    @type  keys_root_dir: string
    
    @param cert_root_dir: absolute path to the root directory in which the certs for
                          all repos will be stored
    @type  cert_root_dir: string

    @param repo_id: identifies the repo in the repo file to delete
    @type  repo_id: string

    @param lock: if the default lock is unacceptble, it may be overridden in this variable
    @type  lock: L{Lock}
    '''

    if not lock:
        lock = Lock('/var/run/subsys/pulp/repolib.pid')

    lock.acquire()
    try:
        log.info('Unbinding repo [%s]' % repo_id)

        if not os.path.exists(repo_filename):
            return

        # Repo file changes
        repo_file = RepoFile(repo_filename)
        repo_file.load()
        repo_file.remove_repo_by_name(repo_id) # will not throw an error if repo doesn't exist
        repo_file.save()

        # Mirror list removal
        if os.path.exists(mirror_list_filename):
            os.remove(mirror_list_filename)

        # Keys removal
        repo_keys = RepoKeyFiles(keys_root_dir, repo_id)
        repo_keys.update_filesystem()
        
        # cert removal
        certificates = CertFiles(cert_root_dir, repo_id)
        certificates.apply()
            
    finally:
        lock.release()


def mirror_list_filename(dir, repo_id):
    '''
    Generates the full path to a unique mirror list file for the given repo.

    @param dir: directory in which mirror list files are stored
    @type  dir: string

    @param repo_id: id of the repo the mirror list will belong to
    @type  repo_id: string
    '''
    return os.path.join(dir, repo_id + '.mirrorlist')

# -- private -----------------------------------------------------------------

def _convert_repo(repo_id, enabled, name):
    '''
    Converts the dict repository representation into the repo file domain instance.
    This will *not* populate the baseurl parameter of the repo. That will be done
    elsewhere to take into account if a mirror list is required depending on the
    host URLs sent with the bind response.

    @param repo_id: The repository unique ID.
    @type repo_id: str

    @param enabled: The repository enabled flag.
    @type enabled: bool

    @param name: The repository name.
    @type name: str

    @return: repo instance in the repo file format
    @rtype:  L{Repo}
    '''
    repo = Repo(repo_id)
    repo['name'] = name
    repo['enabled'] = str(int(enabled))
    return repo

def _handle_gpg_keys(repo, gpg_keys, keys_root_dir):
    '''
    Handles the processing of any GPG keys that were specified with the repo. The key
    files will be written to disk, deleting any existing key files that were there. The
    repo object will be updated with any values related to GPG key information.
    '''

    repo_keys = RepoKeyFiles(keys_root_dir, repo.id)

    if gpg_keys is not None and len(gpg_keys) > 0:
        repo['gpgcheck'] = '1'

        for key_name in gpg_keys:
            repo_keys.add_key(key_name, gpg_keys[key_name])

        key_urls = ['file:' + kfn for kfn in repo_keys.key_filenames()]
        repo['gpgkey'] = '\n'.join(key_urls)
    else:
        repo['gpgcheck'] = '0'
        repo['gpgkey'] = None

    # Call this in either case to make sure any existing keys were deleted
    repo_keys.update_filesystem()
    
def _handle_certs(repo, rootdir, cacert, clientcert):
    '''
    Handle x.509 certificates that were specified with the repo.
    The cert files will be written to disk, deleting any existing
    files that were there. The repo object will be updated with any
    values related to the stored certificates.
    '''
    certificates = CertFiles(rootdir, repo.id)
    certificates.update(cacert, clientcert)
    capath, clientpath = certificates.apply()
    # CA certificate
    if cacert:
        repo['sslcacert'] = capath
        repo['sslverify'] = '1'
    else:
        repo['sslverify'] = '0'
    # client certificate
    if clientcert:
        repo['sslclientcert'] = clientpath

def _handle_host_urls(repo, url_list, mirror_list_filename):
    '''
    Handles the processing of the host URLs sent for a repo. If a mirror list file is
    needed, it will be created and saved to disk as part of this call. The repo
    object will be updated with the appropriate parameter for the repo URL.
    '''

    if len(url_list) > 1:

        # The mirror list file isn't loaded; if this call was made as part of a
        # repo update the file should be written new given the URLs passed in
        mirror_list_file = MirrorListFile(mirror_list_filename)
        mirror_list_file.add_entries(url_list)
        mirror_list_file.save()

        repo['mirrorlist'] = 'file:' + mirror_list_filename
        repo['baseurl'] = None # make sure to zero this out in case of an update

        log.info('Created mirrorlist for repo [%s] at [%s]' % (repo.id, mirror_list_filename))
    else:

        # On a repo update, the mirror list may have existed but is no longer used.
        # If we're in this block there shouldn't be a mirror list file for the repo,
        # so delete it if it's there.
        if os.path.exists(mirror_list_filename):
            os.remove(mirror_list_filename)

        repo['baseurl'] = url_list[0]
        repo['mirrorlist'] = None # make sure to zero this out in case of an update

        log.info('Configuring repo [%s] to use baseurl [%s]' % (decode_unicode(repo.id), url_list[0]))
