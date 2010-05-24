#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Mike McCune
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

from pulp.pexceptions import PulpException

class Base(dict):
    '''
    Base object that has convenience methods to get and put
    attrs into the base dict object with dot notation
    '''
    def __getattr__(self, attr):
        return self.get(attr, None)
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

class Repo(Base):
    def __init__(self, id, name, arch, source):
        self.source = source
        self.repo_source = RepoSource(source)
        self.id = id
        self.name = name
        self.arch = arch
        self.packages = dict()
        
    def get_repo_source(self):
        return RepoSource(self.source)
    
        
class RepoSource(Base):
    # yum:http://blah.bloop.com
    
    def __init__(self, url):
        self.supported_types = ['yum', 'local', 'rhn']
        self.type = None
        self.url = None
        self.parse_feed(url)
        
    def parse_feed(self, source):
        parts = source.split(':')
        if (len(parts) < 2):
            msg = "Invalid feed url.  Must be <type>:<path> where types are: %s"
            raise PulpException(msg % supported_types)
        if (self.supported_types.count(parts[0]) < 1):
            raise PulpException("Invalid type.  valid types are %s" 
                                % self.supported_types)
        self.type = parts[0]
        self.url = source.replace((self.type + ":"), "")


class Package(Base):
    def __init__(self, id, description):
        self.id = id
        self.description = description
        self.versions = []

class PackageVersion(Base):
    def __init__(self, packageid, epoch, version, release, arch):
        self.packageid = packageid
        self.epoch = epoch
        self.version = version
        self.release = release
        self.arch = arch
        self.requires = []
        self.provides = []

class PackageGroup(Base):
    def __init__(self, groupid, name, description):
        self.groupid = groupid
        self.name = name
        self.description = description
        self.mandatory_packages = {}
        self.optional_packages = {}
        self.default_packages = {}
        self.conditional_packages = {}

class Category(Base):
    def __init__(self, categoryid, name, description):
        self.categoryid = categoryid
        self.name = name
        self.description = description
        self.packagegroups = []

class Consumer(Base):
    def __init__(self, id, description):
        self.id = id
        self.description = description
        self.packageids = []
