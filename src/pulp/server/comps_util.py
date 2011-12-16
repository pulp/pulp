#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


# Python
import gzip
import logging
import xml.dom.minidom

# 3rd Party
import yum.comps

import pulp.server

log = logging.getLogger(__name__)

def yum_group_to_model_group(obj):
    """
    Translate a yum.comps.Group to a model.PackageGroup
    @param obj: yum.comps.Group object
    @return: model.PackageGroup object
    """
    grp = pulp.server.db.model.PackageGroup(obj.groupid, obj.name,
        obj.description, obj.user_visible, obj.display_order, obj.default, 
        obj.langonly)
    grp['mandatory_package_names'].extend(obj.mandatory_packages.keys())
    grp['optional_package_names'].extend(obj.optional_packages.keys())
    grp['default_package_names'].extend(obj.default_packages.keys())
    grp['conditional_package_names'] = obj.conditional_packages
    grp['translated_name'] = obj.translated_name
    grp['translated_description'] = obj.translated_description
    return grp

def yum_category_to_model_category(obj):
    """
    Translate a yum.comps.Category to a model.PackageGroupCategory
    @param obj: yum.comps.Category object
    @return: model.PackageGroupCategory object
    """
    ctg = pulp.server.db.model.PackageGroupCategory(obj.categoryid,
        obj.name, obj.description, obj.display_order)
    groupids = [grp for grp in obj.groups]
    ctg['packagegroupids'].extend(groupids)
    ctg['translated_name'] = obj.translated_name
    ctg['translated_description'] = obj.translated_description
    return ctg

def model_group_to_yum_group(obj):
    """
    Translate a model.PackageGroup to a yum.comps.Group
    @param obj: model.PackageGroup obj
    @return: yum.comps.Group object
    """
    grp = yum.comps.Group()
    grp.name = obj['name']
    grp.description = obj['description']
    grp.user_visible = obj['user_visible']
    grp.display_order = obj['display_order']
    grp.default = obj['default']
    grp.langonly = obj['langonly']
    grp.groupid = obj['id']
    for key in obj['translated_name']:
        grp.translated_name[key] = obj['translated_name'][key]
    for key in obj['translated_description']:
        grp.translated_description[key] = obj['translated_description'][key]
    for pkgname in obj['mandatory_package_names']:
        grp.mandatory_packages[pkgname] = 1 
    for pkgname in obj['optional_package_names']:
        grp.optional_packages[pkgname] = 1
    for pkgname in obj['default_package_names']:
        grp.default_packages[pkgname] = 1
    for pkgname in obj['conditional_package_names']:
        grp.conditional_packages[pkgname] = \
                obj['conditional_package_names'][pkgname]
    return grp

def model_category_to_yum_category(obj):
    """
    Translate a model.PackageGroupCategory to an object that 
    yum.comps.Comps can work with
    @param obj: model.PackageGroupCategory object
    @return: yum.comps.Category
    """
    cat = yum.comps.Category()
    cat.name = obj['name']
    cat.description = obj['description']
    cat.display_order = obj['display_order']
    cat.categoryid = obj['id']
    for key in obj['translated_name']:
        cat.translated_name[key] = obj['translated_name'][key]
    for key in obj['translated_description']:
        cat.translated_description[key] = obj['translated_description'][key]
    for groupid in obj['packagegroupids']:
        cat._groups[groupid] = groupid
    return cat

def form_comps_xml(ctgs, grps):
    """
    Form the XML representation of a 'comps.xml' from 
    model.PackageGroupCategories and model.PackageGroup objects
    @param ctgs: List of model.PackageGroupCategories
    @param grps:  List of model.PackageGroup
    @return: unicode string representing XML data for 
    passed in Categories/Groups
    """
    newComps = yum.comps.Comps()
    for cid in ctgs:
        category = model_category_to_yum_category(ctgs[cid])
        newComps.add_category(category)
    for gid in grps:
        pkggrp = model_group_to_yum_group(grps[gid])
        newComps.add_group(pkggrp)
    return newComps.xml()



def update_repomd_xml_string(repomd_xml, compsxml_checksum,
        compsxml_timestamp, compsxml_gz_checksum=None,
        open_compsxml_gz_checksum=None, compsxml_gz_timestamp=None):
    """
    Accept input xml string of repomd data and update it with new comps info
    @param repomd_xml: string repomd_xml
    @param compsxml_checksum: checksum of compsxml file
    @param compsxml_timestamp: timestamp of compsxml file
    @param compsxml_gz_checksum: checksum of compsxml gzipped file
    @param open_compsxml_gz_checksum: checksum of compsxml gzipped file uncompressed
    @param compsxml_gz_timestamp: timestamp of compsxml gzipped file
    """
    dom = xml.dom.minidom.parseString(repomd_xml)
    group_elems = filter(lambda x: x.getAttribute("type") == "group", dom.getElementsByTagName("data"))
    if len(group_elems) > 0:
        elem = group_elems[0].getElementsByTagName("checksum")[0]
        elem.childNodes[0].data = compsxml_checksum
        elem = group_elems[0].getElementsByTagName("timestamp")[0]
        elem.childNodes[0].data = compsxml_timestamp
    else:
        # If no group info is present, then we need to create it.
        repomd_elems = dom.getElementsByTagName("repomd")
        if len(repomd_elems) < 1:
            raise Exception("Unable to find 'repomd' element in %s" % (repomd_xml))
        data_elem = dom.createElement("data")
        data_elem.setAttribute("type", "group")

        loc_elem = dom.createElement("location")
        loc_elem.setAttribute("href", "repodata/comps.xml")
        data_elem.appendChild(loc_elem)

        checksum_elem = dom.createElement("checksum")
        checksum_elem.setAttribute("type", "sha256")
        checksum_value = dom.createTextNode(compsxml_checksum)
        checksum_elem.appendChild(checksum_value)
        data_elem.appendChild(checksum_elem)

        ts_elem = dom.createElement("timestamp")
        ts_value = dom.createTextNode("%s" % (compsxml_timestamp))
        ts_elem.appendChild(ts_value)
        data_elem.appendChild(ts_elem)
        repomd_elems[0].appendChild(data_elem)

    if compsxml_gz_checksum is not None and open_compsxml_gz_checksum is not None \
            and compsxml_gz_timestamp is not None:
        group_gz_elems = filter(lambda x: x.getAttribute("type") == "group_gz",
                dom.getElementsByTagName("data"))
        if len(group_gz_elems) > 0:
            elem = group_gz_elems[0].getElementsByTagName("checksum")[0]
            elem.childNodes[0].data = compsxml_gz_checksum
            elem = group_gz_elems[0].getElementsByTagName("open-checksum")[0]
            elem.childNodes[0].data = open_compsxml_gz_checksum
            elem = group_gz_elems[0].getElementsByTagName("timestamp")[0]
            elem.childNodes[0].data = compsxml_gz_timestamp
        else:
            raise Exception("Not implemented, need to add support for creating group_gz metdata info in repomd.xml")
    return dom.toxml()


def update_repomd_xml_file(repomd_path, comps_path, comps_gz_path=None):
    """
    Update the repomd.xml with the checksum info for comps_path
    @param repomd_path: repomd.xml file path
    @param comps_path:  comps.xml file path
    @param comps_gz_path:  optional comps.xml.gz file path
    @return: True if repomd_path has been updated, False otherwise
    """
    compsxml_checksum = pulp.server.util.get_file_checksum(hashtype="sha256",
            filename=comps_path)
    compsxml_timestamp = pulp.server.util.get_file_timestamp(comps_path)
    compsxml_gz_checksum = None
    open_compsxml_gz_checksum = None
    compsxml_gz_timestamp = None
    if comps_gz_path:
        compsxml_gz_checksum = pulp.server.util.get_file_checksum(hashtype="sha256",
                filename=comps_gz_path)
        compsxml_gz_timestamp = pulp.server.util.get_file_timestamp(comps_gz_path)
        uncompressed = gzip.open(comps_gz_path, 'r').read()
        open_compsxml_gz_checksum = compsxml_checksum
    try:
        repomd = open(repomd_path, "r").read()
        updated_xml = update_repomd_xml_string(repomd,
                compsxml_checksum, compsxml_timestamp,
                compsxml_gz_checksum, open_compsxml_gz_checksum,
                compsxml_gz_timestamp)
        open(repomd_path, "w").write(updated_xml.encode("UTF-8"))
        log.info("update_repomd_xml_file completed")
    except xml.dom.DOMException, e:
        log.error(e)
        log.error("Unable to update group info for %s" % (repomd_path))
        return False
    return True
