from unittest import TestCase

from pulpcore.app import urls, viewsets


class TestRouterForNestedViewset(TestCase):
    def test_finds_router(self):
        """
        Test that the function returns the Repositories nested router when given the Importers
        viewset. These are just convenient examples to use for testing.
        """
        viewset = viewsets.ImporterViewSet()
        ret = urls.router_for_nested_viewset(viewset)

        self.assertIn(ret, urls.nested_routers)
        self.assertTrue(ret.nest_prefix, 'repositories')

    def test_not_found(self):
        """
        Test that ValueError is raised then a router cannot be found.
        """
        viewset = viewsets.NamedModelViewSet()
        viewset.nest_prefix = 'foo'
        self.assertRaises(LookupError, urls.router_for_nested_viewset, viewset)
