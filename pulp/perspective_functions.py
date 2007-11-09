from turbogears import widgets
import cherrypy
import logging
import turbogears
from perspectives import PerspectiveManager

log = logging.getLogger("pulp.ui.if_perspective")

def if_perspective(perspective):
    if "perspective" in cherrypy.session:
        session_pers = cherrypy.session['perspective']
        log.debug("pers in session: %s", session_pers.name) 
        return session_pers.name == perspective
    return False 

def get_perspective():
    return PerspectiveManager().get_current_perspective().name 

def add_if_perspective(vars):
    return vars.update({"if_perspective": if_perspective})

def add_get_perspective(vars):
    return vars.update({"get_perspective": get_perspective})


turbogears.view.variable_providers.append(add_if_perspective)
turbogears.view.variable_providers.append(add_get_perspective)

