from pulp.globalwidgets import PerspectiveList, TaskList
from turbogears import widgets
import cherrypy
import logging
import turbogears
from base import PerspectiveManager

log = logging.getLogger("pulp.ui.if_perspective")

def if_perspective(perspective):
    if "perspective" in cherrypy.session:
        session_pers = cherrypy.session['perspective']
        log.debug("pers in session: %s", session_pers.name) 
        return session_pers.name == perspective
    return False 

def get_perspective():
    return PerspectiveManager().get_current_perspective() 

def get_all_perspectives():
    retval =  []
    keys = PerspectiveManager().get_all_perspectives()
    for k in keys:
        retval.append(PerspectiveManager().get_perspective(k))
    return retval

def perspective_list():
    return PerspectiveList().display() 

def task_list():
    return TaskList().display() 

def add_if_perspective(vars):
    return vars.update({"if_perspective": if_perspective})

def add_get_perspective(vars):
    return vars.update({"get_perspective": get_perspective})

def add_get_all_perspectives(vars):
    return vars.update({"get_all_perspectives": get_all_perspectives})

def add_perspective_list(vars):
    return vars.update({"perspective_list": perspective_list})

def add_task_list(vars):
    return vars.update({"task_list": task_list})


turbogears.view.variable_providers.append(add_if_perspective)
turbogears.view.variable_providers.append(add_get_perspective)
turbogears.view.variable_providers.append(add_get_all_perspectives)
turbogears.view.variable_providers.append(add_perspective_list)
turbogears.view.variable_providers.append(add_task_list)

