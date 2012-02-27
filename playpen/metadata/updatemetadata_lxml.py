#!/usr/bin/env python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
#

import os
import time
import sys
import rpmUtils
from lxml import etree
from createrepo import MetaDataGenerator, MetaDataConfig
from createrepo import yumbased, utils
from pulp.server.util import get_repomd_filetype_path

PRIMARY_XML_STR="""<?xml version="1.0" encoding="UTF-8"?>\n <metadata xmlns="http://linux.duke.edu/metadata/common"
xmlns:rpm="http://linux.duke.edu/metadata/rpm" packages="%s"> %s \n</metadata>"""

FILELISTS_XML_STR="""<?xml version="1.0" encoding="UTF-8"?>
<filelists xmlns="http://linux.duke.edu/metadata/filelists" packages="%s"> %s \n </filelists>"""

OTHER_XMl_STR="""<?xml version="1.0" encoding="UTF-8"?>
<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="%s"> %s \n</otherdata>"""

def get_package_xml(pkg):

    ts = rpmUtils.transaction.initReadOnlyTransaction()
    po = yumbased.CreateRepoPackage(ts, pkg)

    metadata = {'primary' : po.xml_dump_primary_metadata(),
                'filelists': po.xml_dump_filelists_metadata(),
                'other'   : po.xml_dump_other_metadata(),
               }
    return metadata

def add_primary(repo_dir, pkg_path):
    print "start Adding primary %s" % time.ctime()
    primary_xml = os.path.join(repo_dir, get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, 'primary'))
    pkg_primary_xml = get_package_xml(pkg_path)['primary']
    PRIMARY_XML_STR_FILLED = PRIMARY_XML_STR % (1, pkg_primary_xml)
    # load the pkg primary xml
    pkg_et = etree.fromstring(PRIMARY_XML_STR_FILLED)
    # load the repo primary.xml
    repo_et = etree.parse(primary_xml)
    # get root element from repo xml
    root = repo_et.getroot()
    #load repo primary xml children
    et_children = root.getchildren()
    et_child_locations = [c[-2].values()[0] for c in et_children]
    for c1 in pkg_et.getchildren():
        if c1[-2].values()[0] in et_child_locations:
            print "exists skipping"
            continue
        root.append(c1)
    new_et_children = root.getchildren()
    print "Current count %s" % len(et_children)
    print "Updated count %s" % len(new_et_children)
    primary_xml = "%s/.repodata/primary.xml" % repo_dir
    # update package count
    root.set('packages', str(len(new_et_children)))
    repo_et.write(primary_xml)
    primary_xml_gz = "%s.gz" % primary_xml
    utils.compressFile(primary_xml, primary_xml_gz, 'gz')
    print "end time %s" % time.ctime()

def remove_primary(repo_dir, pkg_path):
    print "start removing primary %s" % time.ctime()
    primary_xml = os.path.join(repo_dir, get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, 'primary'))
    pkg_primary_xml = get_package_xml(pkg_path)['primary']
    PRIMARY_XML_STR_FILLED = PRIMARY_XML_STR % (1, pkg_primary_xml)
    pkg_et = etree.fromstring(PRIMARY_XML_STR_FILLED)
    repo_et = etree.parse(primary_xml)
    # get root element from repo xml
    root = repo_et.getroot()
    #load repo other xml children
    et_children = root.getchildren()
    et_child_locations = [dict(c.items() + c[0].items()) for c in et_children]
    pkg_et_children = [c[-2].values()[0] for c in pkg_et.getchildren()]
    for c2 in et_children:
        #print c2[-2].values()[0], pkg_et_children
        if c2[-2].values()[0] in pkg_et_children:
            print "removing node %s" % c2.items()
            root.remove(c2)
    new_et_children = root.getchildren()
    print "Current count %s" % len(et_children)
    print "Updated count %s" % len(new_et_children)
    primary_xml = "%s/.repodata/primary.xml" % repo_dir
    # update package count
    root.set('packages', str(len(new_et_children)))
    repo_et.write(primary_xml)
    compute_gzip_xml(primary_xml)
    primary_xml_gz = "%s.gz" % primary_xml
    utils.compressFile(primary_xml, primary_xml_gz, 'gz')
    print "end time %s" % time.ctime()

def add_filelists(repo_dir, pkg_path):
    print "start Adding filelists %s" % time.ctime()
    filelists_xml = os.path.join(repo_dir, get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, 'filelists'))
    node = get_package_xml(pkg_path)['filelists']
    XML_STR_FILLED = FILELISTS_XML_STR % (1, node)
    # load the pkg filelists xml
    pkg_et = etree.fromstring(XML_STR_FILLED)
    # load the repo filelists.xml
    repo_et = etree.parse(filelists_xml)
    # get root element from repo xml
    root = repo_et.getroot()
    #load repo filelists xml children
    et_children = root.getchildren()
    et_child_locations = [dict(c.items() + c[0].items()) for c in et_children]
    for c1 in pkg_et.getchildren():
        pinfo = dict(c1.items() + c1[0].items())
        #for c2 in et_child_locations:
        #    print pinfo, c2
        if pinfo in et_child_locations:
            continue
        root.append(c1)
    new_et_children = root.getchildren()
    print "Current count %s" % len(et_children)
    print "Updated count %s" % len(new_et_children)
    # update package count
    root.set('packages', str(len(new_et_children)))
    filelist_xml = "%s/.repodata/filelists.xml" % repo_dir
    repo_et.write(filelist_xml)
    filelist_xml_gz = "%s.gz" % filelist_xml
    utils.compressFile(filelist_xml, filelist_xml_gz, 'gz')
    print "end time %s" % time.ctime()

def remove_filelists(repo_dir, pkg_path):
    print "start removing filelists %s" % time.ctime()
    filelists_xml = os.path.join(repo_dir, get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, 'filelists'))
    node = get_package_xml(pkg_path)['filelists']
    XML_STR_FILLED = FILELISTS_XML_STR % (1, node)
    pkg_et = etree.fromstring(XML_STR_FILLED)
    repo_et = etree.parse(filelists_xml)
    # get root element from repo xml
    root = repo_et.getroot()
    #load repo other xml children
    et_children = root.getchildren()
    et_child_locations = [dict(c.items() + c[0].items()) for c in et_children]
    pkg_et_children = [dict(c1.items() + c1[0].items()) for c1 in pkg_et.getchildren()]
    for c2 in et_children:
        c2_info = dict(c2.items() + c2[0].items())
        if c2_info in  pkg_et_children:
            print "removing node %s" % c2.items()
            root.remove(c2)
    new_et_children = root.getchildren()
    print "Current count %s" % len(et_children)
    print "Updated count %s" % len(new_et_children)
    # update package count
    root.set('packages', str(len(new_et_children)))
    filelist_xml = "%s/.repodata/filelists.xml" % repo_dir
    repo_et.write(filelist_xml)
    compute_gzip_xml(filelist_xml)
    filelist_xml_gz = "%s.gz" % filelist_xml
    utils.compressFile(filelist_xml, filelist_xml_gz, 'gz')
    print "end time %s" % time.ctime()

def add_otherdata(repo_dir, pkg_path):
    print "start Adding otherdata %s" % time.ctime()
    other_xml = os.path.join(repo_dir, get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, 'other'))
    node = get_package_xml(pkg_path)['other']
    XML_STR_FILLED = OTHER_XMl_STR % (1, node)
    # load the pkg other xml
    pkg_et = etree.fromstring(XML_STR_FILLED)
    # load the repo other.xml
    repo_et = etree.parse(other_xml)
    # get root element from repo xml
    root = repo_et.getroot()
    #load repo other xml children
    et_children = root.getchildren()
    et_child_locations = [dict(c.items() + c[0].items()) for c in et_children]
    for c1 in pkg_et.getchildren():
        pinfo = dict(c1.items() + c1[0].items())
        if pinfo in et_child_locations:
            print "skipping"
            continue
        root.append(c1)
    new_et_children = root.getchildren()
    print "Current count %s" % len(et_children)
    print "Updated count %s" % len(new_et_children)
    # update package count
    root.set('packages', str(len(new_et_children)))
    other_xml = "%s/.repodata/other.xml" % repo_dir
    repo_et.write(other_xml)
    other_xml_gz = "%s.gz" % other_xml
    utils.compressFile(other_xml, other_xml_gz, 'gz')
    print "end time %s" % time.ctime()

def remove_otherdata(repo_dir, pkg_path):
    ## Remove pkgs
    print "start removing otherdata %s" % time.ctime()
    other_xml = os.path.join(repo_dir, get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, 'other'))
    node = get_package_xml(pkg_path)['filelists']
    XML_STR_FILLED = FILELISTS_XML_STR % (1, node)
    pkg_et = etree.fromstring(XML_STR_FILLED)
    repo_et = etree.parse(other_xml)
    # get root element from repo xml
    root = repo_et.getroot()
    #load repo other xml children
    et_children = root.getchildren()
    et_child_locations = [dict(c.items() + c[0].items()) for c in et_children]
    pkg_et_children = [dict(c1.items() + c1[0].items()) for c1 in pkg_et.getchildren()]
    for c2 in et_children:
        c2_info = dict(c2.items() + c2[0].items())
        if c2_info in  pkg_et_children:
            print "removing node %s" % c2.items()
            root.remove(c2)
    new_et_children = root.getchildren()
    print "Current count %s" % len(et_children)
    print "Updated count %s" % len(new_et_children)
    other_xml = "%s/.repodata/other.xml" % repo_dir
    print "writing the xml to disk %s" % time.ctime()
    # update package count
    root.set('packages', str(len(new_et_children)))
    repo_et.write(other_xml)
    other_xml_gz = "%s.gz" % other_xml
    utils.compressFile(other_xml, other_xml_gz, 'gz')
    print "complete the xml to disk %s" % time.ctime()

def parse_args():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-r", "--repodir", dest="repodir", help="repo directory with metadata")
    parser.add_option("-p", "--pkgpath", dest="pkgpath", help="Package location on filesystem")
    parser.add_option("--add", dest="add", action="store_true", help="add a package to repo")
    parser.add_option("--remove", dest="remove", action="store_true", help="remove a package to repo")

    (options, args) = parser.parse_args()
    if not options.add and not options.remove:
        print("add or remove options required")
        sys.exit(-1)

    if not options.repodir:
        print("repodir is required")
        sys.exit(-1)

    if not options.pkgpath:
        print("pkgpath is required")
        sys.exit(-1)

    return options

def setup_metadata_conf(repodir):
    conf = MetaDataConfig()
    conf.directory = repodir
#    conf.update = 1
    conf.database = 1
    conf.verbose = 1
    conf.skip_stat = 1
    return conf

def do_add(repo_dir, pkg_path):
    mdgen = MetaDataGenerator(setup_metadata_conf(repo_dir))
    try:
#        mdgen._setup_old_metadata_lookup()
        print("Adding package %s to repodir %s" % (pkg_path, repo_dir))
        add_primary(repo_dir, pkg_path)
        add_filelists(repo_dir, pkg_path)
        add_otherdata(repo_dir, pkg_path)
        mdgen.doRepoMetadata()
        mdgen.doFinalMove()
    except (IOError, OSError), e:
        raise utils.MDError, ('Cannot access/write repodata files: %s') % e

def do_remove(repo_dir, pkg_path):
    mdgen = MetaDataGenerator(setup_metadata_conf(repo_dir))
    try:
        print("Removing package %s to repodir %s" % (pkg_path, repo_dir))
        remove_primary(repo_dir, pkg_path)
        remove_filelists(repo_dir, pkg_path)
        remove_otherdata(repo_dir, pkg_path)
        mdgen.doRepoMetadata()
        mdgen.doFinalMove()
    except (IOError, OSError), e:
        raise utils.MDError, ('Cannot access/write repodata files: %s') % e

def main():
    options = parse_args()
    repo_dir = options.repodir #"/home/pkilambi/testrepo/"
    pkg_path = options.pkgpath #"/var/lib/pulp/repos/pub/updates/warnerbros-0.1-1.noarch.rpm
    if options.add:
        do_add(repo_dir, pkg_path)

    if options.remove:
        do_remove(repo_dir, pkg_path)

if __name__ == '__main__':
    main()


