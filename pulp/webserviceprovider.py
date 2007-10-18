from turbogears.identity.soprovider import *
from turbogears.identity.visitor import *
import logging
import os
from model import *

log = logging.getLogger("pulp.identity")

class Fake_User(object):
    def __init__(self, user_name):
        self.user_name = user_name
        self.display_name = user_name
        self.permissions = None
        self.groups = None
        return

class FakeIdentity(object):
    def __init__(self, visit_key, user=None):
        log.debug("fakeIdent constructor")
        self._user= user
        self.visit_key= visit_key
   
    def _get_user(self):
        try:
            return self._user
        except AttributeError:
            # User hasn't already been set
            return None
    user= property(_get_user)

    def _get_user_name(self):
        if not self._user:
            return None
        return self._user.user_name
    user_name= property(_get_user_name)

    def _get_display_name(self):
        if not self._user:
            return None
        return self._user.display_name
    display_name= property(_get_display_name)

    def _get_anonymous(self):
        log.debug("get anon")
        return not self._user
    anonymous= property(_get_anonymous)

    def _get_permissions(self):
        try:
            return self._permissions
        except AttributeError:
            # Permissions haven't been computed yet
            return None
    permissions= property(_get_permissions)

    def _get_groups(self):
        try:
            return self._groups
        except AttributeError:
            # Groups haven't been computed yet
            return None
    groups= property(_get_groups)

    def logout(self):
        store = IdentityStore()
        store.remove_identity(self.visit_key)
        anon= FakeIdentity(None,None)
        identity.set_current_identity( anon )
        

class WebServiceIdentityProvider(object):
    def __init__(self):
        super(WebServiceIdentityProvider, self).__init__()
        log.info("WebServiceIdentityProvider starting")

    def create_provider_model(self):
        pass

    def validate_identity(self, user_name, password, visit_key):
        
        log.debug("validate_identity CALLED, username %s, password: %s, visit_key: %s", 
                  user_name, password, visit_key)
        #ul = UserFactory.user_list()
        #for u in ul:
        #    log.debug("user: %s", u.user_name)
        store = IdentityStore()
        if store.get_identity(visit_key):
            log.debug("found in ident store!")
            found = store.get_identity(visit_key)
            return found
        else:
            log.debug("Not found.")
            if ('user_name' in cherrypy.request.params):
                uname_param = cherrypy.request.params['user_name']
                pass_param = cherrypy.request.params['password']
                log.debug("uname_param: %s", cherrypy.request.params['user_name'])
                log.debug("pass_param: %s", cherrypy.request.params['password'])
                if self.validate_password(None, uname_param, pass_param):
                    log.debug("valid password ..")
                    user = Fake_User(user_name)
                    user.display_name = "Mike McUser"
                    set_login_attempted(True)
                    log.debug( "Fake validate_identity %s" % user_name)
                    fi = FakeIdentity(visit_key, user)
                    store.store_identity(fi)
                    return fi;    
                else:
                    log.debug("invalid password, returning none ..")
                    return None
        return None

    def validate_password(self, user, user_name, password):
        log.debug("validate_password CALLED: %s", password)
        #Only accept redhat as the password
        if password == "redhat": 
            log.debug("password is redhat, lets return true")
            return True
        else:
            log.debug("password is NOT REDHAT!")
            return False

    def load_identity(self, visit_key):
        log.debug("load ident: %s", visit_key)
        return self.validate_identity( None, None, visit_key )

    def anonymous_identity( self ):
        log.debug("anonymous_identity CALLED")
        return FakeIdentity( None )

    def authenticated_identity(self, user):
        log.debug("authenticated_identity CALLED")
        return FakeIdentity(None, user)
    
    
class IdentityStore:

    class __impl:
        def __init__(self):
            self.idents = []

        def printid(self):
            print id(self)

        def store_identity(self, ident):
            log.debug("storing identity")
            self.idents.append(ident)
        
        def get_identity(self, visit_key):
            for i in self.idents:
                log.debug("looping over idents")
                if (i.visit_key == visit_key):
                    log.debug("found ident!")
                    return i
        
        def remove_identity(self, visit_key):
            for i in self.idents:
                log.debug("looping over idents")
                if (i.visit_key == visit_key):
                    log.debug("found ident!")
                    self.idents.remove(i)
                    return
                
        
    # storage for the instance reference
    __instance = None

    def __init__(self):
        """ Create singleton instance """
        # Check whether we already have an instance
        if IdentityStore.__instance is None:
            # Create and remember instance
            IdentityStore.__instance = IdentityStore.__impl()

        # Store instance reference as the only member in the handle
        self.__dict__['_Singleton__instance'] = IdentityStore.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)




        
