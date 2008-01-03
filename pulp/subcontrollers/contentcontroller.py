from pulp.model import ContentManager
from pulp.perspectives import Perspective
from turbogears import controllers, expose, identity, widgets, validators, paginate
from turbogears.widgets import Widget, Tabber
from turbogears.widgets.datagrid import *
import logging
import turbogears
log = logging.getLogger("pulp.controllers.contentcontroler")



class ContentController(controllers.Controller):
    
    
    @expose(template="pulp.templates.pulp.content.overview")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='name', limit=10)
    def index(self, **data):
        url = turbogears.url("/pulp/content/details/*id*")
        contentSourceList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('name', 'name', 'Name', 
                options=dict(sortable=True, type='link', href=url)),
            DataGrid.Column('displayName', 'displayName', 'Display Name', 
                options=dict(sortable=True)),
            DataGrid.Column('type', 'type', 'Type', 
                options=dict(sortable=True)),
            
        ])
        
        cm = ContentManager()
        data = cm.list_all_content_sources(identity.current.user.subject)
        return dict(contentSourceList=contentSourceList, data=data)
    
        
    @expose(template="pulp.templates.pulp.content.create")
    @identity.require(identity.not_anonymous())
    def new(self, **data):
        print " Edit : ", id
        form = widgets.TableForm(
            fields=ContentSourceFields(),
            submit_text="Create Content Source"
        )
        return dict(form=form, user={})

    @expose(template="pulp.templates.pulp.content.edit")
    @identity.require(identity.not_anonymous())
    def edit(self, id, **data):
        log.debug(" Edit ..", id)
        form = widgets.TableForm(
            fields=ContentSourceFields(),
            submit_text="Edit Content Source"
        )
        
        source = ContentManager().get_content_source(identity.current.user.subject, id)
        source.url = source.configuration.properties.entry[0].value.stringValue
        log.debug("source! ", source)
        
        return dict(form=form, source=source)


    @expose(template="pulp.templates.pulp.content.sync")
    @identity.require(identity.not_anonymous())
    def sync(self, id, **data):
        log.debug(" Edit ..", id)
        form = widgets.TableForm(
            fields=[widgets.HiddenField(name="id")],
            submit_text="Sync the content!"
        )
        
        source = ContentManager().get_content_source(identity.current.user.subject, id)
        source.url = source.configuration.properties.entry[0].value.stringValue
        log.debug("source! ", source)
        
        return dict(form=form, source=source)

    @expose()
    @identity.require(identity.not_anonymous())
    def performsync(self, **data):
        log.debug("submitted ....")
        # name = data['name']
        # displayName
        cm = ContentManager()
        subject = identity.current.user.subject
        cm.sync_content_source(subject, data.get('id'))
        turbogears.flash("Content now syncing.")
        #raise turbogears.redirect('/pulp/content/details', csid="1")
        raise turbogears.redirect(turbogears.url('/pulp/content/details/' + str(id)))


    @expose(template="pulp.templates.pulp.content.details")
    @identity.require(identity.not_anonymous())
    def details(self, id, **data):
        log.debug(" Details ..", id)
        cm = ContentManager()
        source = cm.get_content_source(identity.current.user.subject, id)
        log.debug("source! ", source)
        template = """<div class="tabber"> 
         <div class="tabbertab"><h2>Tab 1</h2>ContentA</div> 
         <div class="tabbertab"><h2>Tab 2</h2>ContentB</div> 
         <div class="tabbertab"><h2>Tab 3</h2>ContentC</div> 
         </div>"""
        tab = Tabber(template=template)  
        packageCount = cm.get_package_count(identity.current.user.subject, id)
        return dict(source=source, tab=tab, packageCount=packageCount)


    @expose()
    @identity.require(identity.not_anonymous())
    def update(self, **data):
        cm = ContentManager()
        subject = identity.current.user.subject
        id = cm.update_content_source(subject,
                                      data.get('id'),
                                      data.get('name'),
                                      data.get('displayName'),
                                      data.get('description'),
                                      data.get('lazyLoad'),
                                      data['url']
                                      )
        turbogears.flash("Content Source updated.")
        #raise turbogears.redirect('/pulp/content/details', csid="1")
        raise turbogears.redirect(turbogears.url('/pulp/content/details/' + str(id)))

    @expose()
    @identity.require(identity.not_anonymous())
    def create(self, **data):
        log.debug("submitted ....")
        # name = data['name']
        # displayName
        cm = ContentManager()
        subject = identity.current.user.subject
        lazy = str(data.get('lazyLoad') == 'on').lower()
        lazy = str(data.has_key('lazyLoad') and data['lazyLoad'] == 'on').lower()
        id = cm.create_content_source(subject, 
                                      data.get('name'),
                                      data.get('displayName'),
                                      data.get('description'),
                                      lazy,
                                      data.get('url'),
                                      )
        turbogears.flash("New Content Source created.")
        #raise turbogears.redirect('/pulp/content/details', csid="1")
        raise turbogears.redirect('/', csid="1")
        

class MakeImgTag(Widget):
    params = ['field']
    template="""<img src='${tg.url(value)}'></img>"""

def widget_getter(widget, field,**kw):
    def getter(obj,**kw):
            row=obj.id
            return widget.display(field=getattr(row, field, ''))
    return getter



class ContentSourceFields(widgets.WidgetsList):
    # attrs={'size' : '50'}
    name = widgets.TextField(validator=validators.NotEmpty(),
                               name="name", label="Name")
    displayName = widgets.TextField(validator=validators.NotEmpty(),
                               name="displayName", label="Display Name")
    description = widgets.TextArea(name="description", label="Description",
                                    rows=4, cols=40)
    url = widgets.TextField(validator=validators.NotEmpty(),
                               name="url", label="Source URL", attrs={'size' : '50'})
    lazyLoad = widgets.CheckBox(name="lazyLoad", label="Lazy Load")
    id = widgets.HiddenField(name="id")

   
#class ContentSourceValidator(validators.Schema):
#    name = validators.PlainText(not_empty=True)

#class NewContentSourceForm(widgets.Form):
# validator = ContentSourceValidator()
    
    
    
    