from turbogears import controllers, expose, identity
import logging
log = logging.getLogger("pulp.controllers.channelcontroller")

# sub class
class MiddlewareController(controllers.Controller):
    
    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def index(self):
        return dict(mockup_text="Middleware Overview")
    
    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def systems(self, **kw):
        return dict(mockup_text="Middleware Systems")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def users(self, **kw):
        return dict(mockup_text="Middleware Users")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def events(self, **kw):
        return dict(mockup_text="Middleware Events")
