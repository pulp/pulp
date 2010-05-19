#!/usr/bin/env python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# These helper modules are from presto plugin to represent deltarpms
# We will use this until yumrepo supports prestodelta metadata format
#
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

import gzip
try:
    from cElementTree import iterparse
except:
    from xml.etree.cElementTree import iterparse


class DeltaInfo(object):
    """Base Delta rpm info object"""
    def __init__(self, elem):
        self.epoch = elem.get("oldepoch")
        self.version = elem.get("oldversion")
        self.release = elem.get("oldrelease")
        self.filename = None
        self.sequence = None
        self.size = None
        self.checksum = None
        self.checksum_type = None

        for x in elem.getchildren():
            if x.tag == "checksum":
                self.checksum_type = x.get("type")
            setattr(self, x.tag, x.text)

        # Things expect/assume this, might as well help them:
        self.size = long(self.size)

    def evr(self):
        return "%s:%s-%s" % (self.epoch, self.version, self.release)

    def __str__(self):
        return "filename: %s, sequence: %s, size: %d, checksum (%s) = %s" \
                         % (self.filename, self.sequence, self.size, 
                            self.checksum_type, self.checksum)

    def __getitem__(self, key):
        return getattr(self, key)

class NewPackage(object):
    def __init__(self, elem):
        for prop in ("name", "version", "release", "epoch", "arch"):
            setattr(self, prop, elem.get(prop))

        self.deltas = {}
        for child in elem.getchildren():
            if child.tag != "delta":
                continue
            d = DeltaInfo(child)
            self.deltas[d.evr()] = d

    def nevra(self):
        return "%s-%s:%s-%s.%s" % (self.name, self.epoch, self.version,
                                  self.release, self.arch)

    def __str__(self):
        return "%s <== %s" % (self.nevra(), self.deltas)

    def has_key(self, key):
        return self.deltas.has_key(key)
    def __getitem__(self, key):
        return self.deltas[key]

class PrestoParser(object):
    def __init__(self, filename):
        self.deltainfo = {}
        
        if filename.endswith(".gz"):
            fo = gzip.open(filename)
        else:
            fo = open(filename, 'rt')
        for event, elem in iterparse(fo):
            if elem.tag == "newpackage":
                p = NewPackage(elem)
                self.deltainfo[p.nevra()] = p

    def getDeltas(self):
        return self.deltainfo

