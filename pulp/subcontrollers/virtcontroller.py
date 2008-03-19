from turbogears import controllers, expose, identity, paginate
from turbogears.widgets.datagrid import *
from pulp.model.infofeed import InfoFeedService
from pulp.model.virtmanager import VirtManager
from pulp.model.systemmanager import SystemManager
from pulp.perspectives.perspectivesummary import PerspectiveSummaryWidget, PerspectiveSummary
from distributioncontroller import DistributionController
from profilecontroller import ProfileController
from pulp.model.property import Property
import logging
import turbogears
log = logging.getLogger("pulp.controllers.virtcontroller")

# sub class
class VirtController(controllers.Controller):
    
    distribution = DistributionController()
    profile = ProfileController()

    
    @expose(template="pulp.templates.virt.overview")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='id', limit=10)
    def index(self, **kw):
        
        infoFeed = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('event', 'event', 'Event', 
                options=dict(sortable=True, type="Raw")),
            DataGrid.Column('date', 'date', 'Date', 
                options=dict(sortable=True, type="Raw")),

        ])
        data = InfoFeedService().get_virt_feed(identity)
        summaries = []
        summaries.append(PerspectiveSummary("Virtualization", 
                                             "Virtual Host",
                                             "Virtual System"))
        #summaries.append(PerspectiveSummary("Admin", 
        #                                     "systems", 
        #                                     "flib flarb"))
        ps = PerspectiveSummaryWidget(summaries=summaries)
        
        
        return dict(infoFeed=infoFeed, data=data, ps=ps)
    
    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def profiles(self, **kw):
        return dict(mockup_text="Provisioning Profiles")


    @expose(template="pulp.templates.virt.systems")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='id', limit=10)
    def systems (self, **kw):
        systemList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('name', 'name', _('Name'), 
                options=dict(sortable=True)),
            DataGrid.Column('description', 'description', _('Description'), 
                options=dict(sortable=True)),
            DataGrid.Column('id', 'id', _('Add To Tray'), 
                options=dict(sortable=True, type='Checkbox')),
        ])
        
        data = SystemManager().list_systems(None)
        return dict(systemList=systemList, data=data, mockup_text="Systems")

    @expose(template="pulp.templates.virt.provision")
    @identity.require(identity.not_anonymous())
    def provision(self, **kw):
        return dict()

    @expose(template="pulp.templates.virt.control")
    @identity.require(identity.not_anonymous())
    def control(self, **kw):
        return dict()

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def users(self, **kw):
        return dict(mockup_text="Virtualization User Access")

    @expose(template="pulp.templates.mockup")
    @identity.require(identity.not_anonymous())
    def events(self, **kw):
        return dict(mockup_text="Virtualization Events")
