import unittest
import turbogears
from turbogears import testutil
from turbogears.testutil import DummyRequest
from pulp.controllers import Root
from pulp.identity.webserviceprovider import WsUser
from pulp.identity.mockserviceproxy import MockSubject
from pulp.identity.mockserviceproxy import get_mock_WsUser
import cherrypy

cherrypy.root = Root()

class TestPages(unittest.TestCase):

    def setUp(self):
        turbogears.startup.startTurboGears()
        fred = get_mock_WsUser()
        testutil.set_identity_user(fred)


    def tearDown(self):
        """Tests for apps using identity need to stop CP/TG after each test to
        stop the VisitManager thread. 
        See http://trac.turbogears.org/turbogears/ticket/1217 for details.
        """
        turbogears.startup.stopTurboGears()


    def test_indextitle(self):
        "InfoFeed should be in return dict"
        result = self.call(cherrypy.root.index)
        assert result['infoFeed'] is not None
        assert result['data'] is not None
        assert result['ps'] is not None

#    def test_set_perspective(self):
#        try:
#            self.call(cherrypy.root.setperspective, dict(perspective=admin))
#        except Exception:
#            print "got redirect"
#            
#        from pulp.perspectives import PerspectiveManager
#        cp = PerspectiveManager().get_current_perspective()
#        assert cp is not None
#        print "NAME: ", cp.name
#        assert cp.name == "admin"

    def call(self, method, *args, **kw):
        testutil.start_cp()
        output, response = testutil.call_with_request(
            method, PulpDummyRequest(), *args, **kw)
        return output
        
class PulpDummyRequest(DummyRequest):
    params = dict()    
    
