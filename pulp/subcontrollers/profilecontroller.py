from turbogears import controllers, expose, identity, paginate
from turbogears.widgets.datagrid import *
import logging
log = logging.getLogger("pulp.controllers.distributioncontroller")

# sub class
class ProfileController(controllers.Controller):

    @expose(template="pulp.templates.pulp.overview")
    def index(self):
        return dict(mockup_text="Replace Me")

    @expose(template="pulp.templates.virt.profilecreate")
    def create(self):
        return dict(mockup_text="Replace Me")

