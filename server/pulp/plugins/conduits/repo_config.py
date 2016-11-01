"""
This conduit provides the utility methods needed by the distributors API for
configuration validation.
"""

import os

from mongoengine import Q

from pulp.server.db import model


class RepoConfigConduit(object):
    def __init__(self, distributor_type):
        self.distributor_type = distributor_type

    def get_repo_distributors_by_relative_url(self, rel_url, repo_id=None):
        """
        Retrieve a dict containing the repo_id, distributor_id and config for all distributors that
        conflict with the given relative URL. This is agnostic to preceding slashes.

        :param rel_url: a relative URL for a distributor config
        :type  rel_url: basestring
        :param repo_id: the id of a repo to skip, If not specified all repositories will be
                        included in the search
        :type  repo_id: basestring
        :return:        info about each distributor whose configuration conflicts with rel_url
        :rtype:         list of dicts
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
        rel_url_match = Q(config__relative_url={'$regex': '^/?' + working_url + '(/.*|/?\z)'})
        rel_url_in_list = Q(config__relative_url__in=matching_url_list)
        rel_url_is_repo_id = Q(config__relative_url__exists=False) & Q(repo_id=repo_id_url)

        spec = rel_url_is_repo_id | rel_url_in_list | rel_url_match

        if repo_id is not None:
            spec = Q(repo_id__ne=repo_id) & spec

        dists = model.Distributor.objects(spec).only('repo_id', 'config')
        return [{'repo_id': dist.repo_id, '_id': dist.id, 'config': dist.config} for dist in dists]
