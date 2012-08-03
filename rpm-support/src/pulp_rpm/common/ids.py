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

TYPE_ID_DISTRIBUTOR_ISO="iso_distributor"
TYPE_ID_DISTRIBUTOR_YUM="yum_distributor"
TYPE_ID_IMPORTER_YUM="yum_importer"
TYPE_ID_PROFILER_RPM_ERRATA="rpm_errata_profiler"

TYPE_ID_RPM="rpm"
TYPE_ID_SRPM="srpm"
UNIT_KEY_RPM = ("name", "epoch", "version", "release", "arch", "checksum", "checksumtype")


TYPE_ID_ERRATA="erratum"
UNIT_KEY_ERRATA = ("id",)

METADATA_ERRATA = ("title", "description", "version", "release", "type", "status", "updated",
                "issued", "severity", "references", "pkglist", "rights",  "summary",
                "solution", "from_str", "pushcount", "reboot_suggested" )


TYPE_ID_PKG_GROUP="package_group"
TYPE_ID_PKG_CATEGORY="package_category"
#We are adding the 'repo_id' to unit_key for each group/category
#to ensure that each group/category is defined only for that given repo_id
#We do not want to allow sharing a single group or category between repos.
UNIT_KEY_PKG_GROUP = ("id", "repo_id")
METADATA_PKG_GROUP = (  "name", "description", "default", "user_visible", "langonly", "display_order", \
                        "mandatory_package_names", "conditional_package_names",
                        "optional_package_names", "default_package_names",
                        "translated_description", "translated_name")

UNIT_KEY_PKG_CATEGORY = ("id", "repo_id")
METADATA_PKG_CATEGORY = (   "name", "description", "display_order", "translated_name", "translated_description", \
                            "packagegroupids")

TYPE_ID_DISTRO="distribution"
UNIT_KEY_DISTRO = ("id", "family", "variant", "version", "arch")
METADATA_DISTRO = ("files",)

TYPE_ID_DRPM="drpm"
UNIT_KEY_DRPM = ("epoch", "version", "release",  "filename", "checksum", "checksumtype")

METADATA_DRPM = ("size", "sequence", "new_package")
