from turbogears import controllers, expose, identity
from contentcontroller import ContentController
from channelcontroller import ChannelController
import logging
log = logging.getLogger("pulp.controllers.pulpcontroller")

# from pulp.perspectives import Perspective
# from controllers import Root

# sub class
class PulpController(controllers.Controller):
    
    content = ContentController()
    channel = ChannelController()
    
    @expose(template="pulp.templates.pulp.overview")
    def index(self):
        return dict(mockup_text="Welcome to Pulp")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def systems(self, **kw):
        return dict(mockup_text="Systems")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def users(self, **kw):
        return dict(mockup_text="Users")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def policy(self, **kw):
        return dict(mockup_text="Policy")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def events(self, **kw):
        return dict(mockup_text="Events")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def stats(self, **kw):
        return dict(mockup_text="Stats")
