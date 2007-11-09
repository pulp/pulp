import cherrypy
import logging

log = logging.getLogger("pulp.perspectives")

class PerspectiveManager(object):
    
    # Returns the currently used perspetive by the user
    # or will return 'root' as the root perspective if none is
    # in use.
    def get_current_perspective(self):
        if "perspective" in cherrypy.session:
            session_pers = cherrypy.session['perspective']
            log.debug("pers in session: %s", session_pers) 
            return session_pers
        else:
            return self.get_perspective("root")
    
    def set_current_perspective(self, perspective):
        cherrypy.session['perspective'] = perspective
            
    # list of all Perspective objects available
    def get_all_perspectives(self):
        retval = dict()
        retval['root'] = Perspective("root", "/")
        retval['content'] = Perspective("content", "/pulp")
        retval['admin'] = Perspective("admin", "/admin")
        retval['middleware'] = Perspective("middleware", "/middleware")
        return retval
            
    def get_perspective(self, name):
        all = self.get_all_perspectives()
        return all[name]
        

class Perspective(object):
    # Perspective class stores the name and the initial URL
    # to take the user to when switching to that Perspective
    def __init__(self, name, url):
        self.name = name
        self.url = url
        

    