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
import sys, os
import rpmUtils
from createrepo import MetaDataGenerator, MetaDataConfig
from createrepo import yumbased, utils

def get_package_xml(pkg):
    
    ts = rpmUtils.transaction.initReadOnlyTransaction()
    po = yumbased.CreateRepoPackage(ts, pkg)

    metadata = {'primary' : po.xml_dump_primary_metadata(),
                'filelists': po.xml_dump_filelists_metadata(),
                'other'   : po.xml_dump_other_metadata(),
               }
    return metadata

def setup_metadata_conf(repodir):
    conf = MetaDataConfig()
    conf.directory = repodir
    conf.update = 1
    conf.database = 1
    conf.verbose = 1
    conf.skip_stat = 1
    return conf
    
def add_package_to_repo(repodir, packages):
    
    mdgen = MetaDataGenerator(setup_metadata_conf(repodir))
    try:
        mdgen._setup_old_metadata_lookup()
        all_packages = mdgen.getFileList(mdgen.package_dir, '.rpm') + packages
        mdgen.pkgcount = len(all_packages)
        mdgen.openMetadataDocs()
        mdgen.writeMetadataDocs(all_packages)
        mdgen.closeMetadataDocs()
        mdgen.doRepoMetadata()
        mdgen.doFinalMove()
    except (IOError, OSError), e:
        raise utils.MDError, ('Cannot access/write repodata files: %s') % e
     

if __name__ == '__main__': 
    if len(sys.argv) < 2:
        print "USAGE: python updatemetadata_crapi.py <repodir> <pkgname>"
        sys.exit(0)
   
    repodata_xml = get_package_xml(sys.argv[2])
    print repodata_xml['primary']
    add_package_to_repo(sys.argv[1], [os.path.basename(sys.argv[2])])
