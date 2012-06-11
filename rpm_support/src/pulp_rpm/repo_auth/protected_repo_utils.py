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

'''
This module contains utilities for manipulating a local store of protected
repo information.
'''

import os
from threading import RLock

# -- constants ----------------------------------------------------------------------

WRITE_LOCK = RLock()

class ProtectedRepoUtils:

    def __init__(self, config):
        self.config = config

    # -- public -------------------------------------------------------------------------

    def add_protected_repo(self, repo_relative_path, repo_id):
        '''
        Adds a new protected listing and saves the file to disk. If a listing already exists
        for the given URL, it is overwritten.

        This method is preferred over manipulating the listing file itself
        as it ensures locking to prevent concurrent writes.

        @param relative_path_url: relative path for the repo, used to identify the repo
                                  from a request URL
        @type  relative_path_url: str

        @param repo_id: id of the repo, used to look up the repo credentials
        @type  repo_id: str
        '''
        WRITE_LOCK.acquire()

        try:
            f = ProtectedRepoListingFile(self.config.get('repos', 'protected_repo_listing_file'))
            f.load()
            f.add_protected_repo_path(repo_relative_path, repo_id)
            f.save()
        finally:
            WRITE_LOCK.release()

    def delete_protected_repo(self, repo_relative_path):
        '''
        Removes a protected repo listing and saves the file to disk. If the URL
        is not present in the listings, this method has no effect.

        This method is preferred over manipulating the listing file itself
        as it ensures locking to prevent concurrent writes.

        @param relative_path_url: relative path for the repo, this should be the same as
                                  was passed when the repo was initially added
        @type  relative_path_url: str
        '''
        WRITE_LOCK.acquire()

        try:
            f = ProtectedRepoListingFile(self.config.get('repos', 'protected_repo_listing_file'))
            f.load()
            f.remove_protected_repo_path(repo_relative_path)
            f.save()
        finally:
            WRITE_LOCK.release()

    def read_protected_repo_listings(self):
        '''
        Reads in the mapping of relative path URLs to repo ID.

        @param filename: absolute path to the listings file
        @type  filename: str

        @return: mapping of relative path URL to repo ID
        @rtype:  dict {str, str}
        '''
        f = ProtectedRepoListingFile(self.config.get('repos', 'protected_repo_listing_file'))
        f.load()
        return f.listings

# -- classes -------------------------------------------------------------------------

class ProtectedRepoListingFile:

    def __init__(self, filename):
        '''
        @param filename: absolute path to the file; the file does not need to
                         exist at the time of instantiation, the save method will write it
                         out if it doesn't
        @type  filename: string; may not be None

        @raise ValueError: if filename is missing
        '''
        if filename is None:
            raise ValueError('Filename must be specified when creating a ProtectedRepoListingFile')

        self.filename = filename
        self.listings = {} # mapping of relative path to repo ID

    def delete(self):
        '''
        If the repo file exists, it will be deleted. If not, this method does nothing.

        @raise Exception: if there is an error during the delete
        '''
        if os.path.exists(self.filename):
            os.unlink(self.filename)

    def load(self, allow_missing=True):
        '''
        Loads the repo file.

        @param allow_missing: if True, this call will not throw an error if the file cannot
                              be found; defaults to True
        @type  allow_missing: bool

        @raise Exception: if there is an error during the read
        '''
        if allow_missing and not os.path.exists(self.filename):
            return

        f = open(self.filename, 'r')
        contents = f.read()
        f.close()

        # Parse into data structure
        for line in contents.split('\n'):
            pieces = line.split(',')
            if len(pieces) == 2:
                self.listings[pieces[0]] = pieces[1]

    def save(self):
        '''
        Saves the current repositories to the repo file.

        @raise Exception: if there is an error during the write
        '''
        # Make the directory in which the listings file lives if it doesn't exist
        listing_dir = os.path.split(self.filename)[0]
        if not os.path.exists(listing_dir):
            os.makedirs(listing_dir)

        f = open(self.filename, 'w')

        for url in self.listings.keys():
            f.write('%s,%s\n' % (url, self.listings[url]))

        f.close()

    # -- contents manipulation ------------------------------------------------------------

    def add_protected_repo_path(self, relative_path_url, repo_id):
        '''
        Adds a new listing of a protected repo. If a listing already exists
        for the given URL, it is overwritten.

        @param relative_path_url: relative path for the repo, used to identify the repo
                                  from a request URL
        @type  relative_path_url: str

        @param repo_id: id of the repo, used to look up the repo credentials
        @type  repo_id: str
        '''
        self.listings[relative_path_url] = repo_id

    def remove_protected_repo_path(self, relative_path_url):
        '''
        Removes the given repo path from the set of protected repos. If the URL
        is not present in the listings, this method has no effect.

        @param relative_path_url: relative path for the repo; this should be the same
                                  as used when the repo path was first added
        @type  relative_path_url: str
        '''
        self.listings.pop(relative_path_url, None) # will not error if key isn't present
