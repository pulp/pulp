from pulp.model import SystemManager
from turbogears import controllers, expose, identity, paginate
from turbogears.widgets.datagrid import *
from contentcontroller import ContentController
from channelcontroller import ChannelController
import logging
import turbogears
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
    def systemsold(self, **kw):
        return dict(mockup_text="Systems")



    @expose(template="pulp.templates.pulp.systems")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='name', limit=10)
    def systems(self, **data):
        log.debug(" Systems ..", id)
        
        url = turbogears.url("/pulp/system/details/*id*")
        systemList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('name', 'name', _('Name'), 
                options=dict(sortable=True, type='link', href=url)),
            DataGrid.Column('description', 'description', _('Description'), 
                options=dict(sortable=True)),
            DataGrid.Column('packageCount', 'packageCount', _('Package Count'), 
                options=dict(sortable=True)),
        ])
        
        sm = SystemManager()
        data = sm.list_systems(identity.current.user.subject)
        return dict(systemList=systemList, data=data)


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
