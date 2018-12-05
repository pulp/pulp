import pymongo

from pulp.server.db.connection import get_collection
from pulp.server.db.migrations.lib import utils

NEW_FIELD = 'all_profiles_hash'


def migrate_applicability_profile(appl_profile, collection):
    """
    Update an appicability profile.

    Add new field, remove profile data which is available in the consumer_unit_profile collection.

    :param appl_profile: applicability profile to update
    :type  appl_profile: pulp.server.db.model.consumer.RepoProfileApplicability
    :param collection: collection to update
    :type  collection: pymongo.collection.Collection
    """
    delta = {'profile': [],
             NEW_FIELD: appl_profile['profile_hash']}

    collection.update_one({'_id': appl_profile['_id']}, {'$set': delta})


def migrate(*args, **kwargs):
    """
    Add a new field all_profiles_hash. Create new index and drop the old one.
    It's important to drop the old one since it prevents some duplicated records which are now
    possible.

    :param args:   unused
    :type  args:   list
    :param kwargs: unused
    :type  kwargs: dict
    """
    rpa_collection = get_collection('repo_profile_applicability')
    total_profiles = rpa_collection.find({NEW_FIELD: {'$exists': False}}).count()
    appl_profiles = rpa_collection.find({NEW_FIELD: {'$exists': False}}, ['profile_hash'])

    with utils.MigrationProgressLog('Applicability profiles', total_profiles) as migration_log:
        for appl_profile in appl_profiles.batch_size(100):
            migrate_applicability_profile(appl_profile, rpa_collection)
            migration_log.progress()

    rpa_collection.create_index([("all_profiles_hash", pymongo.DESCENDING),
                                 ("profile_hash", pymongo.DESCENDING),
                                 ("repo_id", pymongo.DESCENDING)],
                                unique=True, background=False)

    try:
        rpa_collection.drop_index("profile_hash_-1_repo_id_-1")
    except pymongo.errors.OperationFailure as e:
        if not e.code or e.code == 27:
            # index not found - good, it's been removed before
            pass
        else:
            raise
