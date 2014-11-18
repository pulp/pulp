"""
This conduit provides the utility methods needed by the distributors API for
configuration validation.
"""

import os

from pulp.server.db.model.repository import RepoDistributor


class RepoConfigConduit(object):
    def __init__(self, distributor_type):
        self.distributor_type = distributor_type

    def get_repo_distributors_by_relative_url(self, rel_url, repo_id=None):
        """
        Get the config repo_id and config objects matching a given relative URL. This is agnostic
        to preceding slashes.

        :param rel_url: a relative URL for a distributor config
        :type  rel_url: str

        :param repo_id: the id of a repo to skip, If not specified all repositories will be
                        included in the search
        :type  repo_id: str

        :return:        a cursor to iterate over the list of repository configurations whose
                        configuration conflicts with rel_url
        :rtype:         pymongo.cursor.Cursor
        """

        # build a list of all the sub urls that could conflict with the provided URL.
        current_url_pieces = [x for x in rel_url.split('/') if x]
        matching_url_list = []
        working_url = ''
        for piece in current_url_pieces:
            working_url = os.path.join(working_url, piece)
            matching_url_list.append(working_url)
            matching_url_list.append('/' + working_url)

        # When a relative_url is not specified on repo creation, the url is the repo-id.
        repo_id_url = current_url_pieces[0]

        # Search for all the sub urls as well as any url that would fall within the specified url.
        # The regex here basically matches the a url if it starts with (optional preceding slash)
        # the working url. Anything can follow as long as it is separated by a slash.
        spec = {'$or': [{'config.relative_url': {'$regex': '^/?' + working_url + '(/.*|/?\z)'}},
                        {'config.relative_url': {'$in': matching_url_list}},
                        {'$and': [{'config.relative_url': {'$exists': False}},
                                  {'repo_id': repo_id_url}]}
                        ]}

        if repo_id is not None:
            spec = {'$and': [{'repo_id': {'$ne': repo_id}}, spec]}

        projection = {'repo_id': 1, 'config': 1}
        return RepoDistributor.get_collection().find(spec, projection)
