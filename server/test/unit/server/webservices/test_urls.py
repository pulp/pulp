import unittest

from django.core.urlresolvers import resolve, Resolver404


class TestDjangoPluginsUrls(unittest.TestCase):

    def test_match_distributor_resource_view(self):
        pass

    def test_match_distributors_view(self):
        pass

    def test_match_importer_resource_view(self):
        pass

    def test_match_importers_view(self):
        pass

    def test_match_type_resource_view(self):
        pass

    def test_match_types_view(self):
        pass


class TestDjangoRepoGroupsUrls(unittest.TestCase):
    """
    Test url matching for /repo_groups/*
    """

    def test_match_repo_groups(self):
        pass

    def test_match_repo_group_resource(self):
        pass

    def test_match_repo_group_associate(self):
        pass

    def test_match_repo_group_unassociate(self):
        pass

    def test_match_repo_group_distributors(self):
        pass

    def test_match_repo_group_distributor_resource(self):
        pass

    def test_repo_group_publish(self):
        pass
