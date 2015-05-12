"""
Contains legacy manager code that is required for migrations.
"""

import logging

from pulp.server.db.connection import get_collection
from pulp.server.db import model
from pulp.server.db.model.repository import RepoContentUnit, RepoImporter
from pulp.server.webservices.views import serializers


_logger = logging.getLogger(__name__)


class RepoManager(object):
    """
    Performs repository related functions relating to both CRUD operations and
    actions performed on or by repositories.
    """
    @staticmethod
    def rebuild_content_unit_counts(repo_ids=None):
        """
        WARNING: This might take a long time, and it should not be used unless
        absolutely necessary. Not responsible for melted servers.

        This will iterate through the given repositories, which defaults to ALL
        repositories, and recalculate the content unit counts for each content
        type.

        This method is called from platform migration 0004, so consult that
        migration before changing this method.

        :param repo_ids:    list of repository IDs. DEFAULTS TO ALL REPO IDs!!!
        :type  repo_ids:    list
        """
        association_collection = RepoContentUnit.get_collection()

        # This line is the only difference between this lib and the original manager code. It
        # functions the same way, but the old way of accessing the collection no longer exists.
        repo_collection = get_collection('repos')

        # default to all repos if none were specified
        if not repo_ids:
            repo_ids = [repo['id'] for repo in repo_collection.find(fields=['id'])]

        _logger.info('regenerating content unit counts for %d repositories' % len(repo_ids))

        for repo_id in repo_ids:
            _logger.debug('regenerating content unit count for repository "%s"' % repo_id)
            counts = {}
            cursor = association_collection.find({'repo_id': repo_id})
            type_ids = cursor.distinct('unit_type_id')
            cursor.close()
            for type_id in type_ids:
                spec = {'repo_id': repo_id, 'unit_type_id': type_id}
                counts[type_id] = association_collection.find(spec).count()
            repo_collection.update({'id': repo_id}, {'$set': {'content_unit_counts': counts}},
                                   safe=True)

    @staticmethod
    def find_with_importer_type(importer_type_id):
        """
        This originally lived in the RepoQueryManager.

        This code is now used in a pulp_rpm migration, which is done after the `id` to `repo_id`
        migration.
        """

        results = []
        repo_importers = list(
            RepoImporter.get_collection().find({'importer_type_id': importer_type_id}))
        for ri in repo_importers:
            repo_obj = model.Repository.objects.get(repo_id=ri['repo_id'])
            repo = serializers.Repository(repo_obj).data
            repo['importers'] = [ri]
            results.append(repo)

        return results
