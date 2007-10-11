from turbogears import controllers, expose, flash
from turbogears import widgets, validators, validate, error_handler
from turbogears.widgets import Tabber
import cherrypy
import logging
import turbogears
import xml.dom.minidom
import xmlrpclib
import navbar
import if_path


tabber_widget = widgets.Tabber()
log = logging.getLogger("pulp.controllers")

class Root(controllers.RootController):
    @expose(template="pulp.templates.welcome")
    def index(self, **data):
        import time
        if "locale" in data:
            locale = data['locale']
            turbogears.i18n.set_session_locale(locale)
        # log.debug("Happy TurboGears Controller Responding For Duty")
        flash(_('hello world'))
        return dict(now=time.ctime())

    @expose(template="pulp.templates.login")
    def login(self):
        tabber = PulpTabber()
        login_form = widgets.TableForm(
           fields=LoginFields(),
            action="loginsubmit"
        )
        return dict(path=cherrypy.request.path, 
                    tabber=tabber, login_form=login_form)
        
    @expose(template="pulp.templates.login")
    def loginsubmit(self, **data):
        login = data['login']
        password = data['password']
        


    @expose(template="pulp.templates.login")
    def users(self):
        login_form = widgets.TableForm(
           fields=LoginFields(),
            action="loginsubmit"
        )
        return dict(login_form=login_form)

    @expose(template="pulp.templates.login")
    def groups(self):
        login_form = widgets.TableForm(
           fields=LoginFields(),
            action="loginsubmit"
        )
        return dict(login_form=login_form)

    @expose(template="pulp.templates.search")
    def search(self):
        search_form = widgets.TableForm(
           fields=SearchFields(),
            action="searchsubmit"
        )
        return dict(search_form=search_form)


    @expose(template="pulp.templates.login")
    def resources(self):
        login_form = widgets.TableForm(
           fields=LoginFields(),
            action="loginsubmit"
        )
        return dict(login_form=login_form)

    @expose(template="pulp.templates.login")
    def policy(self):
        login_form = widgets.TableForm(
           fields=LoginFields(),
            action="loginsubmit"
        )
        return dict(login_form=login_form)

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

