from turbogears import controllers, expose, identity, paginate
from turbogears.widgets.datagrid import *
from pulp.model.infofeed import InfoFeedService
from pulp.model.virtmanager import VirtManager
import turbogears
import logging
log = logging.getLogger("pulp.controllers.distributioncontroller")

# sub class
class DistributionController(controllers.Controller):

    
    @expose(template="pulp.templates.virt.distributions")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='name', limit=10)
    def index(self, **kw):
        
        url = turbogears.url("/pulp/channel/details/*id*")
        distroList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('name', 'name', _('Name'), 
                options=dict(sortable=True)),
            DataGrid.Column('type', 'type', _('Type'), 
                options=dict(sortable=True)),
            DataGrid.Column('arch', 'arch', _('Arch'), 
                options=dict(sortable=True)),
                
        ])
        
        vm = VirtManager()
        data = vm.list_all_distros()
        return dict(distroList=distroList, data=data)

    @expose(template="pulp.templates.virt.distrocreate")
    def create(self):
        return dict(mockup_text="Replace Me")

    