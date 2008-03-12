from pulp.model import ChannelManager
from pulp.model import ContentManager
from turbogears import controllers, expose, identity, widgets, validators, \
    paginate
from turbogears.widgets import Widget, Tabber, LinkRemoteFunction, AjaxGrid
from turbogears.widgets.big_widgets import LinkRemoteFunctionDesc
from turbogears.widgets.base import CoreWD
from turbogears.widgets.datagrid import *
import logging
import turbogears
import urllib
import pulp.util

log = logging.getLogger("pulp.controllers.channelcontroller")

class PackageOperation(object):
    '''
    Simple class to hold the field values to display on the picksystems page
    '''
    def __init__(self, name, summary, url, button):
        self.name = name
        self.summary = summary
        self.url = url
        self.button = button
        
class ChannelController(controllers.Controller):
    
    installsystem = PackageOperation("installsystem", _("install packages on:"),\
        turbogears.url("/pulp/channel/installpackagesonsystem/"), _("Install!")) 
    deletefromsystem = PackageOperation("deletefromsystem",\
                                    _("delete packages from:"),\
                                    turbogears.url("/url"), _("Delete!")) 
    deletefromchannel = PackageOperation("deletefromchannel", \
        _("Are you sure you want to delete these packages from this channel?"),\
        "http://url", _("Delete!")) 

    operations = dict()
    operations[installsystem.name] = installsystem
    operations[deletefromsystem.name] = deletefromsystem
    operations[deletefromchannel.name] = deletefromchannel
    
    @expose(template="pulp.templates.pulp.channel.overview")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='name', limit=10)
    def index(self, **data):
        url = turbogears.url("/pulp/channel/details/*id*")
        log.debug("Search: " + str(data.get('search')))
        channelList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('name', 'name', _('Name'), 
                options=dict(sortable=True, type='link', href=url)),
        ])
        
        cm = ChannelManager()
        data = cm.list_all_channels(identity.current.user.subject)        
        return dict(channelList=channelList, data=data)

    
        
    @expose(template="pulp.templates.pulp.channel.create")
    @identity.require(identity.not_anonymous())
    def new(self, **data):
        log.debug(" Edit : ", id)
        form = widgets.TableForm(
            fields=ChannelDetailsFields(),
            submit_text=_("Create Channel")
        )
        return dict(form=form, channel={})

    @expose()
    @identity.require(identity.not_anonymous())
    def create(self, **data):
        cm = ChannelManager()
        subject = identity.current.user.subject
        lazy = str(data.get('lazyLoad') == 'on').lower()
        lazy = str(data.has_key('lazyLoad') and data['lazyLoad'] == 'on').lower()
        name = str(data.get('name'))
        desc = str(data.get('description'))
        id = cm.create_channel(subject, 
                               name,
                               desc)
        turbogears.flash(_("New Channel created."))
        raise turbogears.redirect(turbogears.url('/pulp/channel/details/%s' % \
                                                  str(id)))
    

    @expose(template="pulp.templates.pulp.channel.edit")
    @identity.require(identity.not_anonymous())
    def edit(self, id, **data):
        log.debug(" Edit ..", id)
        form = widgets.TableForm(
            fields=ChannelDetailsFields(),
            submit_text=_("Edit Channel")
        )
        
        channel = ChannelManager().get_channel(identity.current.user.subject, \
                                               id)
        log.debug("channel! ", channel)
        return dict(form=form, channel=channel)

    @expose(template="pulp.templates.pulp.channel.details")
    @identity.require(identity.not_anonymous())
    def details(self, id, **data):
        log.debug(" Details ..", id)
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
                                      data.get('description')
                                      )
        turbogears.flash(_("Channel updated."))
        #raise turbogears.redirect('/pulp/content/details', csid="1")
        raise turbogears.redirect(turbogears.url('/pulp/channel/details/%s' % \
                                                                    str(id)))

    @expose(template="pulp.templates.pulp.channel.addcontent")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='name', limit=10)
    def addcontent(self, id, **data):
        channelList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('name', 'name', _('Name'), 
                options=dict(sortable=True)),
            DataGrid.Column('id', 'id', _('Associate'), 
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
        #if data.has_key('id'):
        if data.get('id') is None:
            turbogears.flash(_("No Content Sources selected."))
        else:
            ids = pulp.util.get_param_as_list('id', data)
            cm.add_content_source(subject, channel_id, ids)                
            turbogears.flash(_("Content added!"))
        raise turbogears.redirect(turbogears.url('/pulp/channel/details/%s' % \
                                                            str(channel_id)))

    
    
    @expose(template="pulp.templates.pulp.channel.packages")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='name', limit=10)
    def packages(self, id, **data):
        log.debug(" Packages ..", id)
        search = data.get('searchstring')
        url = turbogears.url("/pulp/package/details/*id*")
        channel = ChannelManager().get_channel(identity.current.user.subject, \
                                               id)
        packageList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('fileName', 'fileName', _('File Name'), 
                options=dict(sortable=True, type='link', href=url)),
            DataGrid.Column('architecture', 'arch', _('Architecture'), 
                options=dict(sortable=True, type='link', href=url)),
            DataGrid.Column('id', 'id', _('Select Packages'), 
                options=dict(sortable=True, type='Checkbox')),
        ])
        
        cm = ChannelManager()
        data = cm.list_packages_in_channel(identity.current.user.subject, id,\
                                           search)

        return dict(jslink = LinkRemoteFunctionDesc(), channel=channel, packageList=packageList, data=data)

    @expose()
    @identity.require(identity.not_anonymous())
    def operateonpackages(self, channel_id, **data):
        '''
        Forward to the correct location with the right package ids selected
        '''
        ids = data.get('id')
        if data.get('id') is None:
            turbogears.flash(_("No Packages Sources selected."))
        operation = data.get('operation')
        if (operation == self.installsystem.name):
            # cherrypy.session['operation'] = data.get('id')
            ids = pulp.util.get_param_as_list('id', data)
            idparams = []
            for pid in ids:
                 idparams.append(('pvid', pid))
             
            raise turbogears.redirect( \
                            turbogears.url('/pulp/channel/picksystems/%s' % \
                            str(channel_id)) + '/' + operation +'/' + '?' + \
                            urllib.urlencode(idparams))

           
            
        raise turbogears.redirect(turbogears.url('/pulp/channel/details/%s' % \
                                                            str(channel_id)))

    @expose(template="pulp.templates.pulp.channel.picksystems")
    @identity.require(identity.not_anonymous())
    @paginate('subbedsystems', default_order='id', limit=10)
    def picksystems(self, channel_id, operation_name, **data):
        '''
        Pick from list of systems to do stuff to them. (install packages, 
        remove packages, etc..)
        '''
        url = turbogears.url("/pulp/systems/details/*id*")
        operation = self.operations.get(str(operation_name))
        channel = ChannelManager().get_channel(identity.current.user.subject, \
                                               channel_id)
        systemList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('name', 'name', _('Name'), 
                options=dict(sortable=True)),
            DataGrid.Column('description', 'description', _('Description'), 
                options=dict(sortable=True)),
            DataGrid.Column('id', 'id', _('Select'), 
                options=dict(sortable=True, type='Checkbox')),
        ])
        
        packageList = DataGrid(
            fields=[
            DataGrid.Column('fileName', 'fileName', _('File Name'), 
                options=dict(sortable=True, type='link', href=url)),
        ])
        
        cm = ChannelManager()
        subbedsystems = cm.list_systems_subscribed(\
                                identity.current.user.subject, channel_id, None)
        
        pvids = pulp.util.get_param_as_list('pvid', data)
        print "Pvid: " + str(pvids)
        allpackages = cm.list_packages_in_channel(identity.current.user.subject,\
                                            channel_id, None)
        # Filter out selected packages
        selectedpackages = []
        for p in allpackages:
            print "found " + p.id
            if p.id in pvids:
                selectedpackages.append(p)
                
        return dict(operation=operation, channel=channel, \
                    systemList=systemList, packageList=packageList,\
                    subbedsystems=subbedsystems, \
                    selectedpackages=selectedpackages)

    @expose()
    @identity.require(identity.not_anonymous())
    def installpackagesonsystem(self, channel_id, **data):
        cm = ChannelManager()
        subject = identity.current.user.subject
        if data.get('id') is None:
            turbogears.flash(_("No Systems selected."))
        else:
            systemids = pulp.util.get_param_as_list('id', data)
            packageids = pulp.util.get_param_as_list('pvid', data)
            print "Packageids: " + str(packageids)
            cm.install_packages_system(subject, channel_id, systemids,\
                                       packageids)                
            turbogears.flash(_("Packages installing!"))
        raise turbogears.redirect(turbogears.url('/pulp/channel/details/%s' % \
                                                            str(channel_id)))




    @expose(template="pulp.templates.pulp.channel.systems")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='filename', limit=10)
    def systems(self, id, **data):
        log.debug(" Systems ..", id)
        search = data.get('search')
        url = turbogears.url("/pulp/package/details/*id*")
        channel = ChannelManager().get_channel(identity.current.user.subject, \
                                               id)
        
        systemList = PaginateDataGrid(
            template="pulp.templates.dgrid", fields=[
            DataGrid.Column('name', 'name', _('Name'), 
                options=dict(sortable=True)),
            DataGrid.Column('description', 'description', _('Description'), 
                options=dict(sortable=True)),
            DataGrid.Column('id', 'id', _('Subscribe'), 
                options=dict(sortable=True, type='Checkbox')),
        ])
        
        cm = ChannelManager()
        data = cm.list_systems_subscribed(identity.current.user.subject, id,\
                                           search)

        return dict(channel=channel, systemList=systemList, data=data)

    @expose()
    @identity.require(identity.not_anonymous())
    def systemstochannel(self, channel_id, **data):
        cm = ChannelManager()
        subject = identity.current.user.subject
        ids = data.get('id')
        if ids is None:
            turbogears.flash(_("No Systems selected."))
            return dict()
        else:
            if not isinstance(ids, list):
                ids = [ids]
            cm.subscribe_systems(subject, channel_id, ids)                
            turbogears.flash(_("Systems subscribed!"))
        raise turbogears.redirect(turbogears.url('/pulp/channel/details/%s' % \
                                                            str(channel_id)))

class ChannelDetailsFields(widgets.WidgetsList):
    # attrs={'size' : '50'}
    name = widgets.TextField(validator=validators.NotEmpty(),
                               name="name", label="Name", 
                               attrs={'bloop' : 'blarg'} )
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
