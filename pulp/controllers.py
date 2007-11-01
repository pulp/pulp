from channelcontroller import *
from model.infofeed import InfoFeedService
from cherrypy import request, response
from turbogears import controllers, expose, flash, identity, widgets, paginate, redirect
from turbogears import widgets, validators, validate, error_handler
from turbogears.widgets import Tabber
from turbogears.widgets.datagrid import *
import cherrypy
import if_path
import logging
import navbar
import turbogears
import xml.dom.minidom
import xmlrpclib


tabber_widget = widgets.Tabber()
log = logging.getLogger("pulp.controllers")

    
class Root(controllers.RootController):
    @expose(template="pulp.templates.overview")
    @identity.require(identity.not_anonymous())
    @paginate('data', default_order='id', limit=10)
    def index(self, **data):
        import time
        if "locale" in data:
            locale = data['locale']
            turbogears.i18n.set_session_locale(locale)
        # log.debug("Happy TurboGears Controller Responding For Duty")
        infoFeed = PaginateDataGrid(template="pulp.templates.dgrid", fields=[
            DataGrid.Column('perspective', 'perspective', 'Perspective', 
                options=dict(sortable=True, type="Raw")),
            DataGrid.Column('event', 'event', 'Event', 
                options=dict(sortable=True, type="Raw")),
            DataGrid.Column('date', 'date', 'Date', 
                options=dict(sortable=True, type="Raw")),

        ])
        data = InfoFeedService().get_feed(identity)
        return dict(now=time.ctime(), infoFeed=infoFeed, data=data)

    @expose(template="pulp.templates.login")
    def login(self, forward_url=None, previous_url=None, *args, **kw):

        log.debug("anon: %s", identity.current.anonymous)
        log.debug("attempt: %s", identity.was_login_attempted())
        
        if not identity.current.anonymous \
            and identity.was_login_attempted():
            log.debug("redirecting to: %s", forward_url)
            raise redirect(forward_url)

        forward_url=None
        previous_url= request.path

        if identity.was_login_attempted():
            log.debug("1")
            msg=_("The credentials you supplied were not correct or "
                   "did not grant access to this resource.")
        elif identity.get_identity_errors():
            log.debug("2")
            msg=_("You must provide your credentials before accessing "
                   "this resource.")
        else:
            log.debug("3")
            msg=_("Please log in.")
            forward_url= request.headers.get("Referer", "/")
            
        response.status=403
        return dict(message=msg, previous_url=previous_url, logging_in=True,
                    original_parameters=request.params,
                    forward_url=forward_url)

    @expose()
    def logout(self):
        identity.current.logout()
        raise redirect("/")

    @expose(template="pulp.templates.dashboard")
    @identity.require(identity.not_anonymous())
    def dashboard(self, **kw):
        return dict()
    
    @expose(template="pulp.templates.overview")
    @identity.require(identity.not_anonymous())
    def pulp(self, **kw):
        return dict()
    

    @expose(template="pulp.templates.channels.overview")
    @identity.require(identity.not_anonymous())
    def overview(self, **kw):
        search_form = widgets.TableForm(
           fields=SearchFields(),
            action="searchsubmit"
        )
        return dict(search_form=search_form)

    @expose(template="pulp.templates.events")
    @identity.require(identity.not_anonymous())
    def events(self, **kw):
        search_form = widgets.TableForm(
           fields=SearchFields(),
            action="searchsubmit"
        )
        return dict(search_form=search_form)
 
    @expose(template="pulp.templates.search")
    @identity.require(identity.not_anonymous())
    def groups(self, **kw):
        search_form = widgets.TableForm(
           fields=SearchFields(),
            action="searchsubmit"
        )
        return dict(search_form=search_form)

    @expose(template="pulp.templates.search")
    @identity.require(identity.not_anonymous())
    def admin(self, **kw):
        search_form = widgets.TableForm(
           fields=SearchFields(),
            action="searchsubmit"
        )
        return dict(search_form=search_form)


    @expose(template="pulp.templates.search")
    def resources(self, **kw):
        login_form = widgets.TableForm(
           fields=LoginFields(),
            action="loginsubmit"
        )
        return dict(login_form=login_form)

    @expose(template="pulp.templates.search")
    def policy(self, **kw):
        search_form = widgets.TableForm(
           fields=SearchFields(),
            action="searchsubmit"
        )
        return dict(search_form=search_form)

    def xmlrpclogin(self): 
        log.debug("fetch_systems called")
        
        SATELLITE_HOST = "satellite3.pdx.redhat.com"
        SATELLITE_URL = "http://%s/rpc/api" % SATELLITE_HOST
        SATELLITE_LOGIN = "admin"
        SATELLITE_PASSWORD = "redhat"

        client = xmlrpclib.Server(SATELLITE_URL, verbose=0)
        session_key = client.auth.login(SATELLITE_LOGIN, SATELLITE_PASSWORD)
        results = client.system.listUserSystems(session_key)
        return results
    
    channels = ChannelController()
                    
class LoginFields(widgets.WidgetsList):
    login = widgets.TextField(validator=validators.NotEmpty())
    password = widgets.TextField(validator=validators.NotEmpty(),
      attrs={'size':30})

class SearchFields(widgets.WidgetsList):
    search = widgets.TextField(validator=validators.NotEmpty())
    search_type = widgets.SingleSelectField("search_type", 
                                      label=_("Search For:"),   
                                      options=[(1, _("Systems")),   
                                               (2, _("Software")),   
                                               (3, _("Users")),  
                                               (4, _("Events"))],  
                                      default=2)  

