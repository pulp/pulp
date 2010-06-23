#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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


# Python
import logging

# 3rd Party
import yum.comps

import pulp

log = logging.getLogger('pulp.comps_util')

def yum_group_to_model_group(obj):
    """
    Translate a yum.comps.Group to a model.PackageGroup
    @param obj: yum.comps.Group object
    @return: model.PackageGroup object
    """
    grp = pulp.model.PackageGroup(obj.groupid, obj.name, 
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
    ctg = pulp.model.PackageGroupCategory(obj.categoryid, 
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
    for key in obj['conditional_package_names']:
        grp.conditional_packages[key] = obj['conditional_package_names'][key]
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

