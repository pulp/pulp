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
from pulp_rpm.yum_plugin import util

PRIMARY_XML_STR="""<?xml version="1.0" encoding="UTF-8"?>\n <metadata xmlns="http://linux.duke.edu/metadata/common"
xmlns:rpm="http://linux.duke.edu/metadata/rpm" packages="%s"> %s \n</metadata>"""

FILELISTS_XML_STR="""<?xml version="1.0" encoding="UTF-8"?>
<filelists xmlns="http://linux.duke.edu/metadata/filelists" packages="%s"> %s \n </filelists>"""

OTHER_XMl_STR="""<?xml version="1.0" encoding="UTF-8"?>
<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="%s"> %s \n</otherdata>"""

FTYPES_XML_DICT = { 'primary' : PRIMARY_XML_STR,
                    'filelists': FILELISTS_XML_STR,
                    'other': OTHER_XMl_STR
                  }

def get_package_xml(pkg):

    ts = rpmUtils.transaction.initReadOnlyTransaction()
    po = yumbased.CreateRepoPackage(ts, pkg)

    metadata = {'primary' : po.xml_dump_primary_metadata(),
                'filelists': po.xml_dump_filelists_metadata(),
                'other'   : po.xml_dump_other_metadata(),
               }
    return metadata


def add_metadata(repo_dir, pkg_path):
    ftypes = ['primary', 'filelists', 'other']
    for ftype in ftypes:
        print("Processing %s filetype" % ftype)
        ftype_xml = os.path.join(repo_dir, util.get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, ftype))
        node = get_package_xml(pkg_path)[ftype]
        XML_STR_FILLED = FTYPES_XML_DICT[ftype] % (1, node)
        # load the pkg other xml
        pkg_et = etree.fromstring(XML_STR_FILLED)
        # load the repo ftype.xml
        repo_et = etree.parse(ftype_xml)
        # get root element from repo xml
        root = repo_et.getroot()
        #load repo primary xml children
        #pkgs = repo_et.findall("//{http://linux.duke.edu/metadata/common}package")
        et_children = root.getchildren()
        if ftype == 'primary':
            # compare location href
            et_child_locations = [c[-2].get('href') for c in et_children]
            for c1 in pkg_et.getchildren():
                if c1[-2].get('href') in et_child_locations:
                    continue
                root.append(c1)
        else: # if filelists or other
            # compare nvrea + pkgid
            et_child_locations = [dict(c.items() + c[0].items()) for c in et_children]
            for c1 in pkg_et.getchildren():
                pinfo = dict(c1.items() + c1[0].items())
                if pinfo in et_child_locations:
                    continue
                root.append(c1)
        new_et_children = root.getchildren()
        print "Current count %s" % len(et_children)
        print "Updated count %s" % len(new_et_children)
        new_ftype_xml = "%s/.repodata/%s.xml" % (repo_dir, ftype)
        # update package count
        root.set('packages', str(len(new_et_children)))
        # write xml to disk
        repo_et.write(new_ftype_xml)
        ftype_xml_gz = "%s.gz" % new_ftype_xml
        # write compressed xml file
        utils.compressFile(new_ftype_xml, ftype_xml_gz, 'gz')
        print "end time %s" % time.ctime()

def remove_metadata(repo_dir, pkg_path):
    ftypes = ['primary', 'filelists', 'other']
    for ftype in ftypes:
        print("Processing %s filetype" % ftype)
        ftype_xml = os.path.join(repo_dir, util.get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, ftype))
        node = get_package_xml(pkg_path)[ftype]
        XML_STR_FILLED = FTYPES_XML_DICT[ftype] % (1, node)
        # load the pkg other xml
        pkg_et = etree.fromstring(XML_STR_FILLED)
        # load the repo ftype.xml
        repo_et = etree.parse(ftype_xml)
        # get root element from repo xml
        root = repo_et.getroot()
        #load repo ftype xml children
        #pkgs = repo_et.findall("//{http://linux.duke.edu/metadata/common}package")
        et_children = root.getchildren()
        if ftype == 'primary':
            # compare location href
            pkg_et_children = [c[-2].values()[0] for c in pkg_et.getchildren()]
            for c2 in et_children:
                if c2[-2].values()[0] in pkg_et_children:
                    root.remove(c2)
        else: # if filelists or other
            # compare nvrea + pkgid
            pkg_et_children = [dict(c1.items() + c1[0].items()) for c1 in pkg_et.getchildren()]
            for c2 in et_children:
                c2_info = dict(c2.items() + c2[0].items())
                if c2_info in  pkg_et_children:
                    root.remove(c2)
        new_et_children = root.getchildren()
        print "Current count %s" % len(et_children)
        print "Updated count %s" % len(new_et_children)
        new_ftype_xml = "%s/.repodata/%s.xml" % (repo_dir, ftype)
        # update package count
        root.set('packages', str(len(new_et_children)))
        # write xml to disk
        repo_et.write(new_ftype_xml)
        ftype_xml_gz = "%s.gz" % new_ftype_xml
        # write compressed xml file
        utils.compressFile(new_ftype_xml, ftype_xml_gz, 'gz')
        print "end time %s" % time.ctime()

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

    if not os.path.exists(options.pkgpath):
        print("package path %s doesn't exist" %options.pkgpath)
        sys.exit(-1)

    if not os.path.exists(options.repodir):
        print("repo dir path %s doesn't exist" %options.pkgpath)
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
        add_metadata(repo_dir, pkg_path)
        mdgen.doRepoMetadata()
        mdgen.doFinalMove()
    except (IOError, OSError), e:
        raise utils.MDError, ('Cannot access/write repodata files: %s') % e
    except Exception, e:
        print("Unknown Error: %s" % str(e))

def do_remove(repo_dir, pkg_path):
    mdgen = MetaDataGenerator(setup_metadata_conf(repo_dir))
    try:
        print("Removing package %s from repodir %s" % (pkg_path, repo_dir))
        remove_metadata(repo_dir, pkg_path)
        mdgen.doRepoMetadata()
        mdgen.doFinalMove()
    except (IOError, OSError), e:
        raise utils.MDError, ('Cannot access/write repodata files: %s') % e
    except Exception, e:
        print("Unknown Error: %s" % str(e))

def main():
    options = parse_args()
    repo_dir = options.repodir
    pkg_path = options.pkgpath

    if options.add:
        do_add(repo_dir, pkg_path)

    if options.remove:
        do_remove(repo_dir, pkg_path)

if __name__ == '__main__':
    main()


