from turbogears import controllers, expose
import logging
log = logging.getLogger("pulp.controllers.channelcontroller")

# sub class
class ChannelController(controllers.Controller):
    @expose(template="pulp.templates.channels.overview")
    def index(self):
        return dict()
    
    @expose(template="pulp.templates.channels.overview")
    def overview(self):
        return dict()
    
