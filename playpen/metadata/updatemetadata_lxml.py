import rpmUtils
from createrepo import yumbased, utils
from lxml import etree
import time
import sys

XML_STR="""<?xml version="1.0" encoding="UTF-8"?>\n <metadata xmlns="http://linux.duke.edu/metadata/common"
xmlns:rpm="http://linux.duke.edu/metadata/rpm" packages="%s"> %s \n</metadata>"""

def get_package_xml(pkg):

    ts = rpmUtils.transaction.initReadOnlyTransaction()
    po = yumbased.CreateRepoPackage(ts, pkg)

    metadata = {'primary' : po.xml_dump_primary_metadata(),
                'filelists': po.xml_dump_filelists_metadata(),
                'other'   : po.xml_dump_other_metadata(),
               }
    return metadata

def add_package_primary_to_repo(primary_xml_path, pkg_path):
    print "start time %s" % time.ctime()
    node = get_package_xml(pkg_path)['primary']
    XML_STR_FILLED = XML_STR % (1, node)
    print XML_STR_FILLED
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
    repo_et.write("/tmp/foo.xml")
    print "end time %s" % time.ctime()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "USAGE: python updatemetadata_lxml.py <primary_xml> <pkg_path>"
        sys.exit(0)
    primary_xml = sys.argv[1] #"/home/pkilambi/test-primary.xml"
    pkg_path = sys.argv[2] #"/var/lib/pulp/repos/pub/updates/warnerbros-0.1-1.noarch.rpm
    add_package_primary_to_repo(primary_xml, pkg_path)



