from turbogears import controllers, expose, identity
import logging
log = logging.getLogger("pulp.controllers.channelcontroller")

# sub class
class PulpController(controllers.Controller):
    @expose(template="pulp.templates.channels.overview")
    def index(self):
        return dict()
    
    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def channels(self, **kw):
        return dict(mockup_text="Channels")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def content(self, **kw):
        return dict(mockup_text="Content")

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
