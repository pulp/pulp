from turbogears import widgets
import cherrypy
import logging
import turbogears
import perspectives

log = logging.getLogger("pulp.ui.if_perspective")

def if_perspective(perspective):
    if "perspective" in cherrypy.session:
        session_pers = cherrypy.session['perspective']
        log.debug("pers in session: %s", session_pers.name) 
        return session_pers.name == perspective
    return False 

def add_custom_stdvars(vars):
    return vars.update({"if_perspective": if_perspective})

turbogears.view.variable_providers.append(add_custom_stdvars)

