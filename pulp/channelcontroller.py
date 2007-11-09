from turbogears import controllers, expose, identity
import logging
log = logging.getLogger("pulp.controllers.channelcontroller")

# sub class
class ChannelController(controllers.Controller):
    @expose(template="pulp.templates.channels.overview")
    def index(self):
        return dict()
    
    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def channels(self, **kw):
        return dict(mockup_text="Channels")
