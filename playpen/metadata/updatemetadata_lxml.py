import os
import rpmUtils
from createrepo import yumbased, utils
from lxml import etree
import time
import sys
from pulp.server.util import get_repomd_filetype_dump, get_repomd_filetype_path

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

def add_primary(primary_xml_path, pkg_path):
    print "start Adding primary %s" % time.ctime()
    node = get_package_xml(pkg_path)['primary']
    XML_STR_FILLED = PRIMARY_XML_STR % (1, node)
    #print XML_STR_FILLED
    # load the pkg primary xml
    pkg_et = etree.fromstring(XML_STR_FILLED)
    # load the repo primary.xml
    repo_et = etree.parse(primary_xml_path)
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
    repo_et.write("/tmp/foo-primary.xml")
    print "end time %s" % time.ctime()

def add_filelists(filelists_path, pkg_path):
    print "start Adding filelists %s" % time.ctime()
    node = get_package_xml(pkg_path)['filelists']
    XML_STR_FILLED = FILELISTS_XML_STR % (1, node)
    #print XML_STR_FILLED
    # load the pkg filelists xml
    pkg_et = etree.fromstring(XML_STR_FILLED)
    # load the repo primary.xml
    repo_et = etree.parse(filelists_path)
    # get root element from repo xml
    root = repo_et.getroot()
    #load repo primary xml children
    et_children = root.getchildren()
    et_child_locations = [c.items() + c[0].items() for c in et_children]
    for c1 in pkg_et.getchildren():
        pinfo = c1.items() + c1[0].items()
        if pinfo in et_child_locations:
            continue
        root.append(c1)
    new_et_children = root.getchildren()
    print "Current count %s" % len(et_children)
    print "Updated count %s" % len(new_et_children)
    repo_et.write("/tmp/foo-filelists.xml")
    print "end time %s" % time.ctime()

def add_otherdata(otherdata_xml, pkg_path):
    print "start Adding otherdata %s" % time.ctime()
    node = get_package_xml(pkg_path)['other']
    XML_STR_FILLED = OTHER_XMl_STR % (1, node)
    #print XML_STR_FILLED
    # load the pkg other xml
    pkg_et = etree.fromstring(XML_STR_FILLED)
    # load the repo other.xml
    repo_et = etree.parse(otherdata_xml)
    # get root element from repo xml
    root = repo_et.getroot()
    #load repo primary xml children
    et_children = root.getchildren()
    et_child_locations = [c.items() + c[0].items() for c in et_children]
    for c1 in pkg_et.getchildren():
        pinfo = c1.items() + c1[0].items()
        if pinfo in et_child_locations:
            continue
        root.append(c1)
    new_et_children = root.getchildren()
    print "Current count %s" % len(et_children)
    print "Updated count %s" % len(new_et_children)
    repo_et.write("/tmp/foo-other.xml")
    print "end time %s" % time.ctime()

def main():
    repo_dir = sys.argv[1] #"/home/pkilambi/testrepo/"
    pkg_path = sys.argv[2] #"/var/lib/pulp/repos/pub/updates/warnerbros-0.1-1.noarch.rpm
    primary_xml = os.path.join(repo_dir, get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, 'primary'))
    print primary_xml
    add_primary(primary_xml, pkg_path)
    filelists_xml = os.path.join(repo_dir, get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, 'filelists'))
    print filelists_xml
    add_filelists(filelists_xml, pkg_path)
    other_xml = os.path.join(repo_dir, get_repomd_filetype_path("%s/repodata/repomd.xml" % repo_dir, 'other'))
    print other_xml
    add_otherdata(other_xml, pkg_path)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "USAGE: python updatemetadata_lxml.py <repodata_dir> <pkg_path>"
        sys.exit(0)
    main()


