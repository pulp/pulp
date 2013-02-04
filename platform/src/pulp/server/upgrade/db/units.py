# -*- coding: utf-8 -*-
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

"""
Moreso than anywhere else in the DB upgrade process, this script is written
against Pulp at a point in time. It is expected that any changes to the unit
schemas will be done through DB migration scripts. Same with standard
collections such as content_types.

As such, this script intentionally does not use code in pulp.server despite
the obvious temptation. The collection names for each unit is duplicated here;
if it changes in the future, a migration script will move everything and this
script will continue to use the original names. Same goes for the content_types
model. It'd be useful to use the ContentType class, but if that changes, there
is potential that this script would break or the migration to the new changes
would fail, so in the interest of not having to perpetually maintain this
script, that model is duplicated here.

Another aspect of this is the fact that the content types are explicitly set
to version 0. This will cause the migrations to take place to move from that
point in time (which corresponds to before the first migration script being
written) to the latest.

For units only, the Pulp server does not use ObjectId but instead generates
a string using the uuid module. The associations created by this script,
however, must use ObjectId like normal.
"""

from gettext import gettext as _
import datetime
from functools import partial
import hashlib
import os
import uuid

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from pulp.common import dateutils
from pulp.server.compat import ObjectId
from pulp.server.upgrade.model import UpgradeStepReport
from pulp.server.upgrade.utils import presto_parser


# Passed to mongo to scope the returned results to only the RPM unit key

V2_RPM_KEYS_FIELDS = {
    'name' : 1,
    'epoch' : 1,
    'version' : 1,
    'release' : 1,
    'arch' : 1,
    'checksumtype' : 1,
    'checksum' : 1,
}


DIR_STORAGE_ROOT = '/var/lib/pulp/content/'
DIR_RPMS = os.path.join(DIR_STORAGE_ROOT, 'rpm')
DIR_SRPMS = os.path.join(DIR_STORAGE_ROOT, 'srpm')
DIR_DRPM = os.path.join(DIR_STORAGE_ROOT, 'drpm')
DIR_DISTRIBUTION = os.path.join(DIR_STORAGE_ROOT, 'distribution')

PACKAGE_PATH_TEMPLATE = '%(name)s/%(version)s/%(release)s/%(arch)s/%(checksum)s/%(filename)s'

# We don't track this distinction in v1, but the majority of the units in a
# v1 install will have come from a sync, so this is a reasonable default. What
# is lost here is the knowledge of which units were uploaded, where "lost" is
# a misleading term since we never actually had it in v1 in the first place.
DEFAULT_OWNER_TYPE = 'importer'
DEFAULT_OWNER_ID = 'yum_importer'

# More information we don't have in v1. Set the association creation and last
# confirmed time to the time the upgrade is run. Also, this is one of the few
# places I call into our code from the upgrade process; my hope is that we'll
# never change how UTC is generated, which is probably a safe bet.
DEFAULT_CREATED = dateutils.format_iso8601_datetime(datetime.datetime.now(tz=dateutils.utc_tz()))
DEFAULT_UPDATED = DEFAULT_CREATED

# Used when converting the v1 distribution files into v2

# Substitute in distro ID
V1_DISTRO_DIR = '/var/lib/pulp/distributions/%s/'

# Substitute in distro ID and file relative path
V2_DISTRO_FILE_DIR = '/var/lib/pulp/content/distribution/%s/%s/'

# The paths for the files in a v1 distro are hardcoded to /var/lib/pulp/distributions,
# but I can't have the unit test write test data there for permissions reasons.
# The simplest approach is to just skip that portion of the upgrade during
# testing. Not ideal, but let's be honest, this entire upgrade process shouldn't
# be being written in the first place, so I'm willing to cut corners.
SKIP_FILES = False


# Type definition constants located at the end of this file for readability


def upgrade(v1_database, v2_database):
    report = UpgradeStepReport()

    # I expected the return value from these calls to be more meaningful.
    # As it turned out, nearly all of them simply return True. I didn't rip
    # out the result flags yet in case testing shows that they'll be useful,
    # but don't be surprised when this looks kinda pointless after looking at
    # the individual upgrade methods.
    # jdob, Nov 8, 2012

    init_types_success = _initialize_content_types(v2_database)
    init_associations_success = _initialize_association_collection(v2_database)

    rpms_success = _rpms(v1_database, v2_database, report)
    srpms_success = _srpms(v1_database, v2_database, report)
    drpms_success = _drpms(v1_database, v2_database, report)
    errata_success = _errata(v1_database, v2_database, report)
    distributions_success = _distributions(v1_database, v2_database, report)
    iso_success = _isos(v1_database, v2_database, report)

    report.success = (init_types_success and init_associations_success and
                      rpms_success and srpms_success and drpms_success and
                      errata_success and distributions_success and iso_success)
    return report

# -- upgrade steps ------------------------------------------------------------

def _initialize_content_types(v2_database):

    # See module-level docstring for information about why this exists.

    # Collection initialization
    types_coll = v2_database.content_types
    migrations_coll = v2_database.migration_trackers

    # These calls mimic what the base Model class does, which is why the
    # DESCENDING IS used.
    types_coll.ensure_index([('id', DESCENDING)], unique=True)
    migrations_coll.ensure_index([('name', DESCENDING)], unique=True)

    # Idempotency: The type definition id is the uniqueness. There are so few
    # that we can simply iterate over each one to see if it is already in the
    # v2 database.

    for type_def in TYPE_DEFS:
        existing = types_coll.find_one({'id' : type_def['id']})
        if not existing:
            # The ObjectId will be added by mongo, no need to do it here
            types_coll.insert(type_def, safe=True)

            # Apply the uniqueness for the unit key. This is necessary as the
            # upgrade calls in this module rely on that for idempotency checks.
            units_coll = getattr(v2_database, _units_collection_name(type_def['id']))

            # These indexes mimic how the types database code creates indexes,
            # which is admittedly different than how Model uses DESCENDING above.
            unit_index = [(k, ASCENDING) for k in type_def['unit_key']]
            units_coll.ensure_index(unit_index, unique=True)

            # These are less important to the actual execution of the upgrade,
            # but I'd rather have these created now than after the data is
            # inserted
            for search_index in type_def['search_indexes']:
                units_coll.ensure_index(search_index, unique=False)

        existing = migrations_coll.find_one({'name' : type_def['display_name']})
        if not existing:
            new_migration = {
                '_id' : ObjectId(),
                'name' : type_def['display_name'],
                'version' : 0,
            }
            migrations_coll.insert(new_migration, safe=True)

    return True


def _initialize_association_collection(v2_database):

    # Setting the uniqueness constraints to simplify the unit association
    # idempotency checks and simply let the database handle it. Also setting
    # the search indexes so we don't eat that cost at first server start.

    unique_indexes = ( ('repo_id', 'unit_type_id', 'unit_id', 'owner_type', 'owner_id'), )
    search_indexes = ( ('repo_id', 'unit_type_id', 'owner_type'),
                       ('unit_type_id', 'created')
                     )

    # Copied from Model at the time of writing the upgrade
    def _ensure_indexes(collection, indices, unique):
        for index in indices:
            if isinstance(index, basestring):
                index = (index,)
            collection.ensure_index([(i, DESCENDING) for i in index],
                                    unique=unique, background=True)

    ass_coll = v2_database.repo_content_units
    _ensure_indexes(ass_coll, unique_indexes, True)
    _ensure_indexes(ass_coll, search_indexes, False)

    return True


def _rpms(v1_database, v2_database, report):
    rpm_coll = v2_database.units_rpm
    all_rpms = v1_database.packages.find({'arch' : {'$ne' : 'src'}})
    return _packages(v1_database, v2_database, rpm_coll, all_rpms, 'rpm', report)


def _srpms(v1_database, v2_database, report):
    srpm_coll = v2_database.units_srpm
    all_srpms = v1_database.packages.find({'arch' : 'src'})
    return _packages(v1_database, v2_database, srpm_coll, all_srpms, 'srpm', report)


def _packages(v1_database, v2_database, package_coll, all_v1_packages,
              unit_type_id, report):

    # In v1, both RPMs and SRPMs are stored in the packages collection.
    # The differentiating factor is the arch which will be 'src' for SRPMs and,
    # well, not src for normal RPMs. This call handles both cases, with the
    # differentiator being done by the parameters.

    # Idempotency: This one is ugly. The unique key for an RPM/SRPM in v2
    # is NEVRA, checksumtype, and checksum. It's less efficient but way simpler
    # to iterate over each package in v1 and attempt to insert it, letting
    # mongo's uniqueness check prevent a duplicate.

    for v1_rpm in all_v1_packages:
        new_rpm_id = str(uuid.uuid4())
        v2_rpm = {
            'name' : v1_rpm['name'],
            'epoch' : v1_rpm['epoch'],
            'version' : v1_rpm['version'],
            'release' : v1_rpm['release'],
            'arch' : v1_rpm['arch'],
            'description' : v1_rpm['description'],
            'vendor' : v1_rpm['vendor'],
            'filename' : v1_rpm['filename'],
            'requires' : v1_rpm['requires'],
            'provides' : v1_rpm['provides'],
            'buildhost' : v1_rpm['buildhost'],
            'license' : v1_rpm['license'],

            '_id' : new_rpm_id,
            '_content_type_id' : unit_type_id
        }

        # Checksum is weird, it's stored as a dict of checksum type to the
        # checksum value. In practice the data should never contain multiple
        # entries (instead, multiple documents would be created in the packages
        # collection), so if we encouter it warn the user and only store the
        # first entry.
        if len(v1_rpm['checksum']) > 1:
            warning = _('Multiple checksums found for the RPM %(filename)s,'
                        'only the checksum of type %(type)s will be saved')
            report.warning(warning % {'filename' : v1_rpm['filename'], 'type' : v1_rpm['checksum'].keys()[0]})

        v2_rpm['checksumtype'] = v1_rpm['checksum'].keys()[0]
        v2_rpm['checksum'] = v1_rpm['checksum'][v2_rpm['checksumtype']]

        # Relative path will be set during the associations. That information
        # is only obtainable from a repo itself in v1. Not ideal, but so far
        # one of the very few places where it's a multi-step process to upgrade
        # a data type.

        # Storage path
        rpm_path = PACKAGE_PATH_TEMPLATE % v2_rpm
        storage_path = os.path.join(DIR_RPMS, rpm_path)
        v2_rpm['_storage_path'] = storage_path

        try:
            package_coll.insert(v2_rpm, safe=True)
        except DuplicateKeyError:
            # I really dislike this pattern, but it's easiest. This is the
            # idempotency check and isn't a problem that needs to be handled.

            # Still should try to do the association in the event the unit
            # was added but the association failed.
            unit_key_fields = ('name', 'epoch', 'version', 'release', 'arch',
                               'checksumtype', 'checksum')
            query = dict([ (k, v2_rpm[k]) for k in unit_key_fields ])
            existing = package_coll.find_one(query, {'_id' : 1})
            new_rpm_id = existing['_id']

        _associate_package(v1_database, v2_database, v1_rpm['_id'], new_rpm_id, unit_type_id)

    return True


def _associate_package(v1_database, v2_database, v1_id, v2_id, unit_type):

    v1_coll = v1_database.repos
    v2_coll = v2_database.repo_content_units

    # Idempotency: Easiest to let mongo handle it on insert

    repos_with_package = v1_coll.find({'packages' : v1_id}, {'id' : 1})

    for repo in repos_with_package:
        new_association = {
            '_id' : ObjectId(),
            'repo_id' : repo['id'],
            'unit_id' : v2_id,
            'unit_type_id' : unit_type,
            'owner_type' : DEFAULT_OWNER_TYPE,
            'owner_id' : DEFAULT_OWNER_ID,
            'created' : DEFAULT_CREATED,
            'updated' : DEFAULT_UPDATED,
        }
        try:
            v2_coll.insert(new_association, safe=True)
        except DuplicateKeyError:
            # Still hate this model, still the simplest
            pass


def _drpms(v1_database, v2_database, report):
    v2_coll = v2_database.units_drpm
    v1_coll = v1_database.repos
    v2_ass_coll = v2_database.repo_content_units
    repos = v1_coll.find()
    for repo in repos:
        deltarpms = presto_parser.get_deltas(repo)
        new_associations = []
        for nevra, dpkg in deltarpms.items():
            for drpm in dpkg.deltas.values():
                drpm_id = str(uuid.uuid4())
                new_drpm = {
                    "_id" : drpm_id,
                    "_storage_path" : os.path.join(DIR_DRPM, drpm.filename),
                    "checksumtype" : drpm.checksum_type,
                    "sequence" : drpm.sequence,
                    "checksum" : drpm.checksum,
                    "filename" : drpm.filename,
                    "new_package" : nevra,
                    "epoch" : drpm.epoch,
                    "version" : drpm.version,
                    "release" : drpm.release,
                    "size" : drpm.size,
                    }
                try:
                    v2_coll.insert(new_drpm, safe=True)
                except DuplicateKeyError:
                    # Still hate this model, still the simplest
                    pass
                new_association = {
                    '_id' : ObjectId(),
                    'repo_id' : repo['id'],
                    'unit_id' : drpm_id,
                    'unit_type_id' : 'drpm',
                    'owner_type' : DEFAULT_OWNER_TYPE,
                    'owner_id' : DEFAULT_OWNER_ID,
                    'created' : DEFAULT_CREATED,
                    'updated' : DEFAULT_UPDATED,
                }
                new_associations.append(new_association)
        if new_associations:
            try:
                v2_ass_coll.insert(new_associations, safe=True)
            except DuplicateKeyError, e:
                pass
    return True


def _errata(v1_database, v2_database, report):

    v1_coll = v1_database.errata
    v2_coll = v2_database.units_erratum
    v2_ass_coll = v2_database.repo_content_units

    # Idempotency: We're lucky here, the uniqueness is just by ID, so we can
    # do a pre-fetch and determine what needs to be added.

    v2_errata_ids = [x['id'] for x in v2_coll.find({}, {'id' : 1})]
    missing_v1_errata = v1_coll.find({'id' : {'$nin' : v2_errata_ids}})

    for v1_erratum in missing_v1_errata:
        erratum_id = str(uuid.uuid4())
        new_erratum = {
            '_id' : erratum_id,
            '_storage_path' : None,
            'description' : v1_erratum['description'],
            'from_str' : v1_erratum['from_str'],
            'id' : v1_erratum['id'],
            'issued' : v1_erratum['issued'],
            'pkglist' : v1_erratum.get('pkglist', []),
            'pushcount' : v1_erratum['pushcount'],
            'reboot_suggested' : v1_erratum['reboot_suggested'],
            'references' : v1_erratum['references'],
            'release' : v1_erratum['release'],
            'rights' : v1_erratum['rights'],
            'severity' : v1_erratum['severity'],
            'solution' : v1_erratum['solution'],
            'status' : v1_erratum['status'],
            'summary' : v1_erratum['summary'],
            'title' : v1_erratum['title'],
            'type' : v1_erratum['type'],
            'updated' : v1_erratum['updated'],
            'version' : v1_erratum['version'],
        }
        v2_coll.insert(new_erratum, safe=True)

        # Throughout most of the upgrade scripts, they can be cancelled and
        # resumed at any point and it will do the right thing. In this case,
        # it's a nightmare to cross-reference the v1 erratum against the v2
        # _id field. So adding the association here isn't 100% safe in the event
        # the user ctrl+c's the upgrade (which they shouldn't do anyway) but
        # it's close enough.
        new_associations = []
        for repo_id in v1_erratum['repoids']:
            new_association = {
                '_id' : ObjectId(),
                'repo_id' : repo_id,
                'unit_id' : erratum_id,
                'unit_type_id' : 'erratum',
                'owner_type' : DEFAULT_OWNER_TYPE,
                'owner_id' : DEFAULT_OWNER_ID,
                'created' : DEFAULT_CREATED,
                'updated' : DEFAULT_UPDATED,
            }
            new_associations.append(new_association)

        if new_associations:
            v2_ass_coll.insert(new_associations, safe=True)

    return True


def _distributions(v1_database, v2_database, report):

    # Idempotency: Like RPMs/SRPMs, this is ugly due to the complex key that
    # makes up unique distributions. It's complicated by the fact that in v1,
    # there is no uniqueness contraint on the collection, so it's possible
    # (however unlikely) that we'll run into data integrity issues.

    v1_coll = v1_database.distribution
    v2_coll = v2_database.units_distribution
    v2_ass_coll = v2_database.repo_content_units

    all_v1_distros = v1_coll.find()
    for v1_distro in all_v1_distros:
        new_distro = {
            '_id' : str(uuid.uuid4()),
            '_content_type_id' : 'distribution',
            'id' : v1_distro['id'],
            'arch' : v1_distro['arch'],
            'version' : v1_distro['version'],
            'variant' : v1_distro['variant'],
            'family' : v1_distro['family'],
        }

        # Storage path
        distro_path = os.path.join(DIR_DISTRIBUTION, new_distro['id'])
        new_distro['_storage_path'] = distro_path

        # Upgrade the files format. The .treeinfo file was inventoried in v1
        # but not v2, so strip that out first
        v1_distro_files = [f for f in v1_distro['files'] if '.treeinfo' not in f]
        new_distro['files'] = map(partial(_convert_distribution_file, v1_distro=v1_distro),
                                  v1_distro_files)

        try:
            v2_coll.insert(new_distro, safe=True)
            _associate_distribution(v1_distro, new_distro, v2_ass_coll)
        except DuplicateKeyError:
            # Same pattern as for RPMs, try to insert and rely on the uniqueness
            # check in the DB to enforce idempotency.
            pass

    return True


def _convert_distribution_file(v1_file, v1_distro):
    """
    The format for files changed significantly in v2. In v1 it's simply a list
    of paths to each file on disk. In v2, each file entry is a dict that
    carries a lot of extra data about the file.

    :param v1_file: v1 representation of the file (just its file path) being
                    converted
    :type  v1_file: str

    :param v1_distro: the v1 model for the distribution being converted
    :type  v1_distro: dict

    :return: entry that should be added to the files list in the v2 model
    :rtype:  dict
    """

    distro_id = v1_distro['id']

    # Relative Path
    v1_prefix = V1_DISTRO_DIR % distro_id
    relative_path = v1_file[len(v1_prefix):]

    # File Stats
    checksum = None
    file_size = None
    if not SKIP_FILES:
        checksum = _calculate_checksum(v1_file)
        file_size = os.path.getsize(v1_file)

    # File Name
    filename = os.path.basename(v1_file)

    # v2 Location for the File
    pkg_path_suffix = os.path.dirname(relative_path)
    pkg_path = V2_DISTRO_FILE_DIR % (distro_id, pkg_path_suffix)

    v2_file = {
        'checksum' : checksum,
        'checksumtype' : 'sha256',
        'fileName' : filename,
        'filename' : filename, # This makes me feel dirty
        'item_type' : 'tree_file',
        'pkgpath' : pkg_path,
        'relativepath' : relative_path,
        'size' : file_size,

        'downloadurl' : None, # Unused and not yet removed from the data model
        'savepath' : None, # Unused and not yet removed from the data model
    }

    return v2_file


def _associate_distribution(v1_distribution, v2_distribution, v2_ass_coll):

    # This functions just like errata associations so check _errata for comments
    # on this approach.

    new_associations = []
    for repo_id in v1_distribution['repoids']:
        new_association = {
            '_id' : ObjectId(),
            'repo_id' : repo_id,
            'unit_id' : v2_distribution['_id'],
            'unit_type_id' : 'distribution',
            'owner_type' : DEFAULT_OWNER_TYPE,
            'owner_id' : DEFAULT_OWNER_ID,
            'created' : DEFAULT_CREATED,
            'updated' : DEFAULT_UPDATED,
        }
        new_associations.append(new_association)

    if new_associations:
        v2_ass_coll.insert(new_associations, safe=True)


def _package_groups(v1_database, v2_database, report):

    # In v2, the unique identifier for a package group is the
    # pairing of the group ID and the repository it's in. In v1, the package
    # group is embedded in the repo document itself, which is where we get
    # that information from.

    # In v1 the repository owns the relationship to a package group. Don't look
    # at the model class itself, it wasn't added there, but the code will still
    # stuff it in under the key "packagegroups". The value at that key is a dict
    # of group ID to a PackageGroup instance (v1 model).

    # Idempotency: The simplest way to handle this is to pre-load the set of
    # repo ID/group ID tuples into memory and verify each group found in each
    # v1 repo against that to determine if it has successfully been added or
    # not. The nice part about this over letting the uniqueness checks in mongo
    # itself is that we can batch the group inserts.

    v2_coll = v2_database.units_package_group
    v2_ass_coll = v2_database.repo_content_units

    # Tuple of repo ID and group ID
    already_added_tuples = [ (x['repo_id'], x['id']) for x in
                             v2_coll.find({}, {'repo_id' : 1, 'id' : 1}) ]

    v1_repos = v1_database.repos.find({}, {'id' : 1, 'packagegroups' : 1})
    for v1_repo in v1_repos:

        for group_id in v1_repo.get('packagegroups', {}).keys():

            # Idempotency check
            if (v1_repo['id'], group_id) in already_added_tuples:
                continue

            v1_group = v1_repo['packagegroups'][group_id]
            v2_group_id = str(uuid.uuid4())
            new_group = {
                '_id' : v2_group_id,
                '_storage_path' : None,
                '_content_type_id' : 'package_group',
                'conditional_package_names' : v1_group['conditional_package_names'],
                'default' : v1_group['default'],
                'default_package_names' : v1_group['default_package_names'],
                'description' : v1_group['description'],
                'display_order' : v1_group['display_order'],
                'id' : v1_group['id'],
                'langonly' : v1_group['langonly'],
                'mandatory_package_names' : v1_group['mandatory_package_names'],
                'name' : v1_group['name'],
                'optional_package_names' : v1_group['optional_package_names'],
                'repo_id' : v1_repo['id'],
                'translated_description' : v1_group['translated_description'],
                'translated_name' : v1_group['translated_name'],
                'user_visible' : v1_group['user_visible'],
            }
            v2_coll.insert(new_group, safe=True)

            new_association = {
                '_id' : ObjectId(),
                'repo_id' : v1_repo['id'],
                'unit_id' : v2_group_id,
                'unit_type_id' : 'package_group',
                'owner_type' : DEFAULT_OWNER_TYPE,
                'owner_id' : DEFAULT_OWNER_ID,
                'created' : DEFAULT_CREATED,
                'updated' : DEFAULT_UPDATED,
            }
            v2_ass_coll.insert(new_association, safe=True)

    return True


def _package_group_categories(v1_database, v2_database, report):

    # These act nearly identically to groups, so see the comments in there
    # for more information.

    # Idempotency: As with groups, pre-load the tuples of repo ID to category
    # ID into memory and use that to check for the category's existed before
    # inserting.

    v2_coll = v2_database.units_package_category
    v2_ass_coll = v2_database.repo_content_units

    # Tuple of repo ID and group ID
    already_added_tuples = [ (x['repo_id'], x['id']) for x in
                             v2_coll.find({}, {'repo_id' : 1, 'id' : 1}) ]

    v1_repos = v1_database.repos.find({}, {'id' : 1, 'packagegroupcategories' : 1})
    for v1_repo in v1_repos:

        for category_id in v1_repo.get('packagegroupcategories', {}).keys():

            # Idempotency check
            if (v1_repo['id'], category_id) in already_added_tuples:
                continue

            v1_category = v1_repo['packagegroupcategories'][category_id]
            category_id = str(uuid.uuid4())
            new_category = {
                '_id' : category_id,
                '_storage_path' : None,
                '_content_type_id' : 'package_category',
                'description' : v1_category['description'],
                'display_order' : v1_category['display_order'],
                'id' : v1_category['id'],
                'name' : v1_category['name'],
                'packagegroupids' : v1_category['packagegroupids'],
                'repo_id' : v1_repo['id'],
                'translated_description' : v1_category['translated_description'],
                'translated_name' : v1_category['translated_name'],
            }
            v2_coll.insert(new_category, safe=True)

            new_association = {
                '_id' : ObjectId(),
                'repo_id' : v1_repo['id'],
                'unit_id' : category_id,
                'unit_type_id' : 'package_category',
                'owner_type' : DEFAULT_OWNER_TYPE,
                'owner_id' : DEFAULT_OWNER_ID,
                'created' : DEFAULT_CREATED,
                'updated' : DEFAULT_UPDATED,
            }
            v2_ass_coll.insert(new_association, safe=True)

    return True


def _isos(v1_database, v2_database, report):

    v1_repo_coll = v1_database.repos
    v2_ass_coll = v2_database.repo_content_units
    v2_iso_coll = v2_database.units_iso

    # Idempotency: I still dislike this as a strategy, but the easiest approach
    # is to attempt the insert and let the uniqueness check kick out anything
    # that's already been added.

    v1_files = v1_database.file.find()
    for v1_file in v1_files:
        new_iso_id = str(uuid.uuid4())

        v2_iso = {
            '_id' : new_iso_id,
            '_content_type_id' : 'iso',
            'name' : v1_file['filename'],
            'size' : v1_file['size'],
        }

        # Checksum is stored as a dict from type to checksum, but in v1 we
        # only ever used sha256. The model has been flattened in 2.0 to just
        # store the checksum itself.
        v2_iso['checksum'] = v1_file['checksum'].values()[0]

        try:
            v2_iso_coll.insert(v2_iso, safe=True)
        except DuplicateKeyError:
            # Still try to do the association in the event the unit already
            # existed, so find the existing unit for its ID.
            spec = dict([ (k, v2_iso[k]) for k in v2_iso if k in ('name', 'checksum', 'size')])
            existing = v2_iso_coll.find_one(spec)
            new_iso_id = existing['_id']

        repos_with_iso = v1_repo_coll.find({'files' : v1_file['_id']}, {'id' : 1})
        for v1_repo in repos_with_iso:
            new_association = {
                '_id' : ObjectId(),
                'repo_id' : v1_repo['id'],
                'unit_id' : new_iso_id,
                'unit_type_id' : 'iso',
                'owner_type' : DEFAULT_OWNER_TYPE,
                'owner_id' : DEFAULT_OWNER_ID,
                'created' : DEFAULT_CREATED,
                'updated' : DEFAULT_UPDATED,
                }
            try:
                v2_ass_coll.insert(new_association, safe=True)
            except DuplicateKeyError:
                # Still hate this model, still the simplest
                pass

    return True


# -- really private -----------------------------------------------------------

def _units_collection_name(type_id):
    # Again, the pulp.server code for generating this isn't used to prevent
    # issues if this scheme changes in the future (such a change will be applied
    # later in a migration script).

    return 'units_%s' % type_id


def _calculate_checksum(file_path):
    """
    Ghetto method to calculate and return the SHA256 checksum of a file.
    """

    buffer_size = 65536
    f = open(file_path, 'r')
    f.seek(0, 0)

    m = hashlib.new('sha256')

    try:
        while True:
            buffer = f.read(buffer_size)
            if not buffer:
                break
            m.update(buffer)
    finally:
        f.close()

    return m.hexdigest()

# -- point in time data -------------------------------------------------------

# Values for all type definitions at the point in Pulp's release cycle where
# the upgrade is expected to move to. Any changes that occur after that point
# will be handled by the pulp-manage-db script.
TYPE_DEFS = [
    {
        'id' : 'distribution',
        'display_name' : 'Distribution',
        'description' : 'Kickstart trees and all accompanying files',
        'unit_key' : ['id',  'family', 'variant', 'version', 'arch'],
        'search_indexes' : ['id', 'family', 'variant', 'version', 'arch'],
        'referenced_types' : [],
        },

    {
        'id' : 'drpm',
        'display_name' : 'DRPM',
        'description' : 'DRPM',
        'unit_key' :
            ['epoch',  'version', 'release', 'filename', 'checksumtype', 'checksum'],
        'search_indexes' :
            ['epoch',  'version', 'release', 'checksum', 'filename'],
        'referenced_types' : [],
    },

    {
        'id' : 'erratum',
        'display_name' : 'Erratum',
        'description' : 'Erratum advisory information',
        'unit_key' :
            ['id'],
        'search_indexes' : [
            'title', 'version', 'release', 'type',
            'status', 'updated', 'issued', 'severity', 'references'
        ],
        'referenced_types' : ['rpm'],
    },

    {
        'id' : 'package_group',
        'display_name' : 'Package Group',
        'description' : 'Yum Package group information',
        'unit_key' :
            ['id', 'repo_id'],
        'search_indexes' :
            ['repo_id', 'name', 'mandatory_package_names', 'conditional_package_names',
             'optional_package_names', 'default_package_names'],
        'referenced_types' : [],
    },

    {
        'id' : 'package_category',
        'display_name' : 'Package Category',
        'description' : 'Yum Package category information',
        'unit_key' :
            ['id', 'repo_id'],
        'search_indexes' :
            ['repo_id', 'name', 'packagegroupids'],
        'referenced_types' : [],
    },

    {
        'id' : 'rpm',
        'display_name' : 'RPM',
        'description' : 'RPM',
        'unit_key' :
            ['name', 'epoch', 'version', 'release', 'arch', 'checksumtype', 'checksum'],
        'search_indexes' :
            ['name', 'epoch', 'version', 'release', 'arch', 'filename', 'checksum', 'checksumtype'],
        'referenced_types' : ['erratum']
    },

    {
        'id' : 'srpm',
        'display_name' : 'SRPM',
        'description' : 'SRPM',
        'unit_key' :
            ['name', 'epoch', 'version', 'release', 'arch', 'checksumtype', 'checksum'],
        'search_indexes' :
            ['name', 'epoch', 'version', 'release', 'arch', 'filename', 'checksum', 'checksumtype'],
        'referenced_types' : [],
    },

    {
        'id': 'iso',
        'display_name': 'ISO',
        'description': 'ISO',
        'unit_key': ['name', 'checksum', 'size'],
        'search_indexes': [],
        'referenced_types' : [],
    },
]
