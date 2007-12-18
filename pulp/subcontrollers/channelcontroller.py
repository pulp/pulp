from pulp.model import ChannelManager
from pulp.model import ContentManager
from turbogears import controllers, expose, identity, widgets, validators, \
    paginate
from turbogears.widgets import Widget, Tabber
from turbogears.widgets.datagrid import *
import logging
import turbogears
log = logging.getLogger("pulp.controllers.contentcontroler")

# sub class
class ChannelController(controllers.Controller):
    
    @expose(template="pulp.templates.pulp.channel.overview")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='name', limit=10)
    def index(self, **data):
        url = turbogears.url("/pulp/channel/details/*id*")
        channelList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('name', 'name', 'Name', 
                options=dict(sortable=True, type='link', href=url)),
            DataGrid.Column('displayName', 'displayName', 'Display Name', 
                options=dict(sortable=True)),
        ])
        
        cm = ChannelManager()
        data = cm.list_all_channels(identity.current.user.subject)        
        return dict(channelList=channelList, data=data)

    
        
    @expose(template="pulp.templates.pulp.channel.create")
    @identity.require(identity.not_anonymous())
    def new(self, **data):
        print " Edit : ", id
        form = widgets.TableForm(
            fields=ChannelDetailsFields(),
            submit_text="Create Channel"
        )
        return dict(form=form, channel={})

    @expose()
    @identity.require(identity.not_anonymous())
    def create(self, **data):
        cm = ChannelManager()
        subject = identity.current.user.subject
        lazy = str(data.get('lazyLoad') == 'on').lower()
        lazy = str(data.has_key('lazyLoad') and data['lazyLoad'] == 'on').lower()
        id = cm.create_channel(subject, 
                                      data.get('name'),
                                      data.get('displayName'),
                                      data.get('description'))
        turbogears.flash("New Channel created.")
        raise turbogears.redirect(turbogears.url('/pulp/channel/details/%s' % \
                                                  str(id)))
    

    @expose(template="pulp.templates.pulp.channel.edit")
    @identity.require(identity.not_anonymous())
    def edit(self, id, **data):
        print " Edit ..", id
        form = widgets.TableForm(
            fields=ChannelDetailsFields(),
            submit_text="Edit Channel"
        )
        
        channel = ChannelManager().get_channel(identity.current.user.subject, \
                                               id)
        print "channel! ", channel
        return dict(form=form, channel=channel)

    @expose(template="pulp.templates.pulp.channel.details")
    @identity.require(identity.not_anonymous())
    def details(self, id, **data):
        print " Details ..", id
        channel = ChannelManager().get_channel(identity.current.user.subject, \
                                               id)
        packageCount = ChannelManager().get_package_count(\
                                        identity.current.user.subject, id)
        return dict(channel=channel, packageCount=packageCount)


    @expose()
    @identity.require(identity.not_anonymous())
    def update(self, **data):
        cm = ChannelManager()
        subject = identity.current.user.subject
        id = cm.update_channel(subject,
                                      data.get('id'),
                                      data.get('name'),
                                      data.get('displayName'),
                                      data.get('description')
                                      )
        turbogears.flash("Channel updated.")
        #raise turbogears.redirect('/pulp/content/details', csid="1")
        raise turbogears.redirect(turbogears.url('/pulp/channel/details/%s' % \
                                                                    str(id)))

    @expose(template="pulp.templates.pulp.channel.addcontent")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='name', limit=10)
    def addcontent(self, id, **data):
        channelList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('displayName', 'displayName', 'Display Name', 
                options=dict(sortable=True)),
            DataGrid.Column('id', 'id', 'Associate', 
                options=dict(sortable=True, type='Checkbox')),
        ])
        channel = ChannelManager().get_channel(identity.current.user.subject, \
                                       id)

        cm = ContentManager()
        data = cm.list_all_content_sources(identity.current.user.subject)
        return dict(channel=channel, channelList=channelList, data=data)
    
    @expose()
    @identity.require(identity.not_anonymous())
    def contenttochannel(self, channel_id, **data):
        cm = ChannelManager()
        subject = identity.current.user.subject
        ids = data.get('id')
        if ids is None:
            turbogears.flash("No Content Sources selected.")
        else:
            if not isinstance(ids, list):
                ids = [ids]
            cm.add_content_source(subject, channel_id, ids)                
            turbogears.flash("Content added!")
        raise turbogears.redirect(turbogears.url('/pulp/channel/details/%s' % \
                                                            str(channel_id)))

    
    
    @expose(template="pulp.templates.pulp.channel.packages")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='filename', limit=10)
    def packages(self, id, **data):
        print " Packages ..", id
        url = turbogears.url("/pulp/package/details/*id*")
        channel = ChannelManager().get_channel(identity.current.user.subject, \
                                               id)
        
        packageList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('fileName', 'fileName', 'File Name', 
                options=dict(sortable=True, type='link', href=url)),
            DataGrid.Column('architecture', 'arch', 'Architecture', 
                options=dict(sortable=True, type='link', href=url)),
            #DataGrid.Column('fileName', 'fileName', 'Name',),
            #DataGrid.Column('arch', 'arch', 'Architecture', 
            #    options=dict(sortable=True)),
        ])
        
        cm = ChannelManager()
        data = cm.list_packages_in_channel(identity.current.user.subject, id)

        return dict(packageList=packageList, data=data)


class ChannelDetailsFields(widgets.WidgetsList):
    # attrs={'size' : '50'}
    name = widgets.TextField(validator=validators.NotEmpty(),
                               name="name", label="Name")
    displayName = widgets.TextField(validator=validators.NotEmpty(),
                               name="displayName", label="Display Name")
    description = widgets.TextArea(name="description", label="Description",
                                    rows=4, cols=40)
    id = widgets.HiddenField(name="id")

   
    
#
#    
#    
#    @expose(template="pulp.templates.pulp.channels.overview")
#    def index(self):
#        return dict()
#    
#    @expose(template="pulp.templates.mockup")
#    @identity.require(identity.not_anonymous())
#    def channels(self, **kw):
#        return dict(mockup_text="Channels")
