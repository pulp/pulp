from turbogears import controllers, expose, identity
# from model.resourcemanager import ResourceManager
import logging
log = logging.getLogger("pulp.controllers.channelcontroller")

# sub class
class AdminController(controllers.Controller):
    
    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def index(self):
        return dict(mockup_text="Admin Overview")
    
    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def systems(self, **kw):
        
        return dict(mockup_text="Admin Systems")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def users(self, **kw):
        return dict(mockup_text="Admin Users")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def events(self, **kw):
        return dict(mockup_text="Admin Events")
