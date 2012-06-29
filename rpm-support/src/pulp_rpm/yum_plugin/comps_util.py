#
# Copyright (c) 2012 Red Hat, Inc.
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
import os
import shutil
import tempfile
import xml.dom.minidom

# 3rd Party
import yum.comps

import util
log = logging.getLogger(__name__)

def yum_group_to_model_group(obj):
    """
    Translate a yum.comps.Group to a dict
    @param obj: yum.comps.Group object
    @return: dict
    """
    grp = {}
    grp['id'] = obj.groupid
    grp['name'] = obj.name
    grp['description'] = obj.description
    grp['user_visible'] = obj.user_visible
    grp['display_order'] = obj.display_order
    grp['default'] = obj.default
    grp['langonly'] = obj.langonly
    grp['mandatory_package_names'] = []
    grp['mandatory_package_names'].extend(obj.mandatory_packages.keys())
    grp['optional_package_names'] = []
    grp['optional_package_names'].extend(obj.optional_packages.keys())
    grp['default_package_names'] = []
    grp['default_package_names'].extend(obj.default_packages.keys())
    # Becareful of issue with package names that contain a dot in their name:
    # Example pymongo exception seen from CentOS repos
    #  InvalidDocument: key 'openoffice.org-langpack-en' must not contain '.'
    #  Seen when a conditional_package_name had data of
    #   <packagereq requires="openoffice.org-core" type="conditional">openoffice.org-langpack-en</packagereq>
    grp['conditional_package_names'] = []
    for pkg_name in obj.conditional_packages:
        grp['conditional_package_names'].append((pkg_name, obj.conditional_packages[pkg_name]))
    grp['translated_name'] = obj.translated_name
    grp['translated_description'] = obj.translated_description
    return grp

def yum_category_to_model_category(obj):
    """
    Translate a yum.comps.Category to a dict
    @param obj: yum.comps.Category object
    @return: dict
    """
    ctg = {}
    ctg['id'] = obj.categoryid
    ctg['name'] = obj.name
    ctg['description'] = obj.description
    ctg['display_order'] = obj.display_order
    ctg['packagegroupids'] = []
    groupids = [grp for grp in obj.groups]
    ctg['packagegroupids'].extend(groupids)
    ctg['translated_name'] = obj.translated_name
    ctg['translated_description'] = obj.translated_description
    return ctg

def unit_to_yum_group(pg_unit):
    """
    Translate a package group unit to a yum.comps.Group
    @param obj: package group unit
    @type obj: pulp.server.content.plugins.model.Unit
    @return: yum.comps.Group object
    """
    return dict_to_yum_group(pg_unit.metadata, group_id=pg_unit.unit_key["id"])

def dict_to_yum_group(obj, group_id=None):
    """
    Translate a package group dict to a yum.comps.Group
    @param obj: package group dict
    @type obj: dict

    @param group_id: optional override for group_id
    @type group_id: str

    @return: yum.comps.Group object
    """
    if group_id is None:
        group_id = obj['id']
    grp = yum.comps.Group()
    grp.groupid = group_id
    grp.name = obj['name']
    grp.description = obj['description']
    grp.user_visible = obj['user_visible']
    grp.display_order = obj['display_order']
    grp.default = obj['default']
    grp.langonly = obj['langonly']
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
    for pkgname, values in obj['conditional_package_names']:
        grp.conditional_packages[pkgname] = values
    return grp

def unit_to_yum_category(cat_unit):
    """
    Translate a package category unit to a yum.comps.Category
    @param obj: package category unit
    @type obj: pulp.server.content.plugins.model.Unit
    @return: yum.comps.Category object
    """
    return dict_to_yum_category(cat_unit.metadata, category_id=cat_unit.unit_key["id"])

def dict_to_yum_category(obj, category_id=None):
    """
    Translate a package category dict to an object that 
    yum.comps.Comps can work with
    @param obj: package category dict
    @type obj: dict

    @param category_id optional override of category id
    @type category_id: str

    @return: dict
    """
    if category_id is None:
        category_id = obj['id']
    cat = yum.comps.Category()
    cat.categoryid = category_id
    cat.name = obj['name']
    cat.description = obj['description']
    cat.display_order = obj['display_order']
    for key in obj['translated_name']:
        cat.translated_name[key] = obj['translated_name'][key]
    for key in obj['translated_description']:
        cat.translated_description[key] = obj['translated_description'][key]
    for groupid in obj['packagegroupids']:
        cat._groups[groupid] = groupid
    return cat

def form_comps_xml_from_units(groups, categories):
    """
    @param groups list of package_group units
    @type groups: {str:pulp.server.content.plugins.model.Unit}

    @param categories list of package_category units
    @type categories: {str:pulp.server.content.plugins.model.Unit}

    @return xml formated representation of comps info
    @rtype: str
    """
    # Translate each unit to an instance of a yum Group/Category
    yum_groups = map(unit_to_yum_group, groups)
    yum_categories = map(unit_to_yum_category, categories)
    return form_comps_xml(yum_groups, yum_categories)


def form_comps_xml(yum_groups, yum_categories):
    """
    Form the XML representation of a 'comps.xml' from Group/Category objects

    @param yum_groups:  List of yum package groups
    @type yum_groups: [yum.comps.Group]

    @param yum_categories: List of yum package categories
    @type yum_categories: [yum.comps.Category]

    @return: string representing XML data for passed in Categories/Groups
    @rtype: str
    """
    new_comps = yum.comps.Comps()
    for g in yum_groups:
        new_comps.add_group(g)
    for c in yum_categories:
        new_comps.add_category(c)
    return new_comps.xml()


def update_repomd_xml_string(repomd_xml, compsxml_path, compsxml_checksum,
        compsxml_timestamp, compsxml_gz_path=None, compsxml_gz_checksum=None,
        open_compsxml_gz_checksum=None, compsxml_gz_timestamp=None):
    """
    Accept input xml string of repomd data and update it with new comps info
    @param repomd_xml: string repomd_xml
    @param compsxml_path: relative path of comps.xml
    @param compsxml_checksum: checksum of compsxml file
    @param compsxml_timestamp: timestamp of compsxml file
    @param compsxml_gz_path: relative path of comps.xml.gz
    @param compsxml_gz_checksum: checksum of compsxml gzipped file
    @param open_compsxml_gz_checksum: checksum of compsxml gzipped file uncompressed
    @param compsxml_gz_timestamp: timestamp of compsxml gzipped file
    """
    #ensure that compsxml_path and compsxml_gz_path are relative to the repo dir
    compsxml_path = compsxml_path[compsxml_path.find("repodata"):]
    compsxml_gz_path = compsxml_gz_path[compsxml_gz_path.find("repodata"):]


    dom = xml.dom.minidom.parseString(repomd_xml)
    group_elems = filter(lambda x: x.getAttribute("type") == "group", dom.getElementsByTagName("data"))
    if len(group_elems) > 0:
        elem = group_elems[0].getElementsByTagName("location")[0]
        elem.setAttribute("href", compsxml_path)
        elem = group_elems[0].getElementsByTagName("checksum")[0]
        elem.childNodes[0].data = compsxml_checksum
        elem.setAttribute("type", "sha")
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
        loc_elem.setAttribute("href", compsxml_path)
        data_elem.appendChild(loc_elem)

        checksum_elem = dom.createElement("checksum")
        checksum_elem.setAttribute("type", "sha")
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
            elem = group_gz_elems[0].getElementsByTagName("location")[0]
            elem.setAttribute("href", compsxml_gz_path)
            elem = group_gz_elems[0].getElementsByTagName("checksum")[0]
            elem.childNodes[0].data = compsxml_gz_checksum
            elem.setAttribute("type", "sha")
            elem = group_gz_elems[0].getElementsByTagName("open-checksum")[0]
            elem.childNodes[0].data = open_compsxml_gz_checksum
            elem = group_gz_elems[0].getElementsByTagName("timestamp")[0]
            elem.childNodes[0].data = compsxml_gz_timestamp
        else:
            # If no group info is present, then we need to create it.
            repomd_elems = dom.getElementsByTagName("repomd")
            if len(repomd_elems) < 1:
                raise Exception("Unable to find 'repomd' element in %s" % (repomd_xml))
            data_elem = dom.createElement("data")
            data_elem.setAttribute("type", "group_gz")

            loc_elem = dom.createElement("location")
            loc_elem.setAttribute("href", compsxml_gz_path)
            data_elem.appendChild(loc_elem)

            checksum_elem = dom.createElement("checksum")
            checksum_elem.setAttribute("type", "sha")
            checksum_value = dom.createTextNode(compsxml_gz_checksum)
            checksum_elem.appendChild(checksum_value)
            data_elem.appendChild(checksum_elem)

            ts_elem = dom.createElement("timestamp")
            ts_value = dom.createTextNode("%s" % (compsxml_gz_timestamp))
            ts_elem.appendChild(ts_value)
            data_elem.appendChild(ts_elem)

            ts_elem = dom.createElement("open-checksum")
            ts_value = dom.createTextNode("%s" % (open_compsxml_gz_checksum))
            ts_elem.appendChild(ts_value)
            data_elem.appendChild(ts_elem)

            repomd_elems[0].appendChild(data_elem)
    return dom.toxml()


def update_repomd_xml_file(repomd_path, comps_path):
    """
    Update the repomd.xml with the checksum info for comps_path
    @param repomd_path: repomd.xml file path
    @param comps_path:  comps.xml file path
    @return: True if repomd_path has been updated, False otherwise
    """

    # Copy comps_f to a new file name prepending the sha256sum to the file name
    comps_orig = comps_path
    compsxml_checksum = util.get_file_checksum(hashtype="sha",
            filename=comps_orig)
    comps_path = os.path.join(os.path.split(comps_orig)[0],
        "%s-%s" % (compsxml_checksum, os.path.split(comps_orig)[1]))
    shutil.copyfile(comps_orig, comps_path)
    compsxml_timestamp = util.get_file_timestamp(comps_path)
    # Create gzipped version of comps.xml
    comps_gz_path_orig = "%s.gz" % (comps_orig)
    f_in = open(comps_path, 'rb')
    f_out = gzip.open(comps_gz_path_orig, 'wb')
    try:
        f_out.writelines(f_in)
    finally:
        f_in.close()
        f_out.close()
    compsxml_gz_checksum = util.get_file_checksum(hashtype="sha",
        filename=comps_gz_path_orig)
    comps_gz_path = os.path.join(os.path.split(comps_orig)[0],
        "%s-%s.gz" % (compsxml_gz_checksum, os.path.split(comps_orig)[1]))
    shutil.move(comps_gz_path_orig, comps_gz_path)
    compsxml_gz_timestamp = util.get_file_timestamp(comps_gz_path)
    # Save current group and group_gz file paths so we may cleanup after the update
    old_mddata = util.get_repomd_filetype_dump(repomd_path)

    try:
        # Update repomd.xml with the new comps information
        f = open(repomd_path, "r")
        try:
            repomd = f.read()
        finally:
            f.close()
        updated_xml = update_repomd_xml_string(repomd,
            comps_path, compsxml_checksum, compsxml_timestamp,
            comps_gz_path, compsxml_gz_checksum, compsxml_checksum,
            compsxml_gz_timestamp)
        f = open(repomd_path, "w")
        try:
            f.write(updated_xml.encode("UTF-8"))
        finally:
            f.close()
        log.info("update_repomd_xml_file completed")
    except xml.dom.DOMException, e:
        log.error(e)
        log.error("Unable to update group info for %s" % (repomd_path))
        return False
    current_mddata = util.get_repomd_filetype_dump(repomd_path)
    # Remove old groups and groups_gz
    if old_mddata.has_key("group") and old_mddata["group"].has_key("location"):
        group_path = os.path.join(os.path.dirname(repomd_path), "../", old_mddata["group"]["location"])
        if old_mddata["group"]["location"] != current_mddata["group"]["location"]:
            # For the case when no change occured to metadata, don't delete the 'old', since 'old' == current
            try:
                if os.path.basename(group_path) != "comps.xml":
                    log.info("Removing old group metadata: %s" % (group_path))
                    os.unlink(group_path)
            except:
                log.exception("Unable to delete old group metadata: %s" % (group_path))
    if old_mddata.has_key("group_gz") and old_mddata["group_gz"].has_key("location"):
        group_gz_path = os.path.join(os.path.dirname(repomd_path), "../", old_mddata["group_gz"]["location"])
        if old_mddata["group_gz"]["location"] != current_mddata["group_gz"]["location"]:
            # For the case when no change occured to metadata, don't delete the 'old', since 'old' == current
            try:
                log.info("Removing old group_gz metadata: %s" % (group_gz_path))
                os.unlink(group_gz_path)
            except:
                log.exception("Unable to delete old group_gz metadata: %s" % (group_gz_path))
    return True
