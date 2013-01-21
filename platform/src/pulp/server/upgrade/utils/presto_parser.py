#
# Copyright (c) 2011 Red Hat, Inc.
#
# These helper modules are from presto plugin to represent deltarpms
# We will use this until yumrepo supports prestodelta metadata format
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
import os
import yum
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
        return "filename: %s, sequence: %s, size: %d, checksum (%s) = %s"\
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


def get_deltas(repo):
    """
    A helper call to lookup repomd.xml for prestodelta info,
    parse the presto delta using PrestoParser and extract
    the deltarpm data.
    @return: dict of nevra as key and delta pkg NewPackage object as value
    """
    repomd_xml_path = repo["repomd_xml_path"]
    if not os.path.exists(repomd_xml_path):
        return {}
    prestodelta_rel_path = __get_repomd_filetype_path(repomd_xml_path, "prestodelta")
    if prestodelta_rel_path is not None:
        prestodelta_path = repomd_xml_path.split("repodata/repomd.xml")[0] + '/' + prestodelta_rel_path
    else:
        # No presto info, no drpms to process
        return {}
    deltas = PrestoParser(prestodelta_path).getDeltas()
    return deltas

def __get_repomd_filetype_path(path, filetype):
    """
    Lookup the metadata file type's path
    """
    rmd = yum.repoMDObject.RepoMD("temp_pulp", path)
    if rmd:
        try:
            data = rmd.getData(filetype)
            return data.location[1]
        except:
            return None
    return None


