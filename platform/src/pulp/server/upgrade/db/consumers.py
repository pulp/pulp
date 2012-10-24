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

from pymongo.objectid import ObjectId

from pulp.server.upgrade.model import UpgradeStepReport


# Since v1 was so tightly coupled to RPMs, there's no reason to have plugin
# hooks for the upgrade. However, we have to account for the fact that the
# repos are in fact RPM repositories. So this reference to a particular plugin
# in the platform makes sense given it's the only code that is specifically
# handling the v1 approach.
YUM_DISTRIBUTOR_ID = 'yum_distributor'

# Same as above for the tight coupling
RPM_TYPE = 'rpm'


def upgrade(v1_database, v2_database):

    # Instead of having to worry about having the consumers and bindings added
    # atomically, they will be added as separate steps. There's a slight
    # duplication in queries with this approach, but it's very minimal and
    # beats having to account for the case where a consumer was ported but
    # something stopped its bindings.

    _consumer_history(v1_database, v2_database)
    _consumers(v1_database, v2_database)

    report = UpgradeStepReport()
    report.succeeded()
    return report


def _consumer_history(v1_database, v2_database):
    v1_coll = v1_database.consumer_history
    v2_coll = v2_database.consumer_history

    # Idempotency: The _id values are retained in the migration, so resolve
    # which ones have not yet been migrated and only load those.
    v2_ids = [x['_id'] for x in list(v2_coll.find({}, {'_id' : 1}))]
    missing_v1_entries = list(v1_coll.find({'_id' : {'$nin' : v2_ids}}))

    v2_entries = []
    for v1_entry in missing_v1_entries:
        v2_entry = {
            '_id' : v1_entry['_id'], # for the uniqueness check in this script
            'id' : v1_entry['_id'], # for weird backward compatibility
            'consumer_id' : v1_entry['consumer_id'],
            'originator' : v1_entry['originator'],
            'type' : v1_entry['type_name'], # intentional rename here for v2
            'details' : v1_entry['details'],
            'timestamp' : v1_entry['timestamp'],
        }
        v2_entries.append(v2_entry)

    if v2_entries:
        v2_coll.insert(v2_entries)


def _consumers(v1_database, v2_database):
    v1_coll = v1_database.consumers
    v2_coll = v2_database.consumers

    # Idempotency: consumer_id is unique, so only process consumers whose ID is
    # not in v2 already
    v2_ids = [x['id'] for x in v2_coll.find({}, {'id' : 1})]
    missing_v1_consumers = v1_coll.find({'id' : {'$nin' : v2_ids}})

    for v1_consumer in missing_v1_consumers:
        v2_consumer = {
            'id' : v1_consumer['id'],
            'display_name' : v1_consumer['id'],
            'description' : v1_consumer['description'],
            'notes' : v1_consumer['key_value_pairs'],
            'capabilities' : v1_consumer['capabilities'],
            'certificate' : v1_consumer['certificate'],
        }
        v2_coll.insert(v2_consumer)

        # Ideally, this should be atomic with the consumer. That's also horribly
        # complicated to attempt to honor. So while there's a small chance the
        # following call could be interrupted and the bindings for this consumer
        # lost, the chance is low enough that I'm willing to take it.
        # jdob, Oct 23, 2012

        _consumer_bindings(v2_database, v1_consumer)

        # This suffers from the same atomic issue, but is even less risky since
        # the consumer will resend this eventually anyway, so if it gets lost
        # it will be replaced.
        _unit_profile(v2_database, v1_consumer)


def _consumer_bindings(v2_database, v1_consumer):
    v2_coll = v2_database.consumer_bindings
    consumer_id = v1_consumer['id']
    repo_ids = v1_consumer['repoids']

    # Idempotency: Uniqueness is determined by the tuple of consumer and repo ID
    bound_repo_ids = [x['repo_id'] for x in v2_coll.find({'consumer_id' : consumer_id})]
    unbound_repo_ids = set(repo_ids) - set(bound_repo_ids)

    new_bindings = []
    for repo_id in unbound_repo_ids:
        binding = {
            'consumer_id' : consumer_id,
            'repo_id' : repo_id,
            'distributor_id' : YUM_DISTRIBUTOR_ID,
        }
        new_bindings.append(binding)

    if new_bindings:
        v2_coll.insert(new_bindings)


def _unit_profile(v2_database, v1_consumer):
    v2_coll = v2_database.consumer_unit_profiles
    consumer_id = v1_consumer['id']

    # Idempotency: There's only a single profile stored in v1, so this check
    # is simply if there's a profile for the consumer
    existing = v2_coll.find_one({'consumer_id' : consumer_id})
    if existing:
        return

    id = ObjectId()
    unit_profile = {
        '_id' : id,
        'id' : id,
        'consumer_id' : consumer_id,
        'content_type' : RPM_TYPE,
        'profile' : v1_consumer['package_profile']
    }
    v2_coll.insert(unit_profile)
