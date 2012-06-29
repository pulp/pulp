#!/usr/bin/env python
# 

import tempfile
from pymongo import Connection

from pulp_rpm.yum_plugin import comps_util


connection = Connection()
db = connection.pulp_database
pkg_groups = [grp for grp in db.units_package_group.find()]
pkg_cats = [grp for grp in db.units_package_category.find()]
print "%s package groups" % (len(pkg_groups))
print "%s package categories" % (len(pkg_cats))

yum_groups = map(comps_util.dict_to_yum_group, pkg_groups)
yum_categories = map(comps_util.dict_to_yum_category, pkg_cats)
comps_xml = comps_util.form_comps_xml(yum_groups, yum_categories)

out_path = tempfile.mktemp()
print "Attempting write to %s" % (out_path)
f = open(out_path, "w")
try:
    try:
        # Issue was seen when we didn't run encode('utf8')
        print "type %s" % (type(comps_xml))
        #f.write(comps_xml)  # resulted in UnicodeEncodeError
        f.write(comps_xml.encode('utf8'))
    except UnicodeEncodeError, e:
        print "Caught exception: %s" % (e)
        print "Unable to %s %s data between %s and %s" % (e.reason, e.message, e.start, e.end)
        print "Problem data is <%s>" % (comps_xml[e.start:e.end])

finally:
    f.close()
print "Successfully wrote %s bytes to %s" % (len(comps_xml), out_path)

