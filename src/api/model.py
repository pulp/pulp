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
    def __init__(self, id, name, arch, feed):
        self.id = id
        self.name = name
        self.arch = arch
        self.feed = feed
        self.packages = dict()

class Package(Base):
    def __init__(self, id, description):
        self.id = id
        self.description = description
        self.versions = []

class Version(Base):
    def __init__(self, id, version_str):
        self.id = id
        self.version_str = version_str
        
class Consumer(Base):
    def __init__(self, id, description):
        self.id = id
        self.description = description
        self.packages = dict()
        self.packageids = []
