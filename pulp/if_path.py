from turbogears import widgets
import cherrypy
import logging
import turbogears


log = logging.getLogger("pulp.if_path")

def if_path(path, template):
    ip = IfPath(path=path, template=template)
    return ip.display()

def add_custom_stdvars(vars):
    return vars.update({"if_path": if_path})

turbogears.view.variable_providers.append(add_custom_stdvars)

class IfPath(widgets.Widget):
    def __init__(self, *args, **kw):
        super(IfPath,self).__init__(*args, **kw)
        self.path = kw['path']
        # self.template = kw['template']

    def display(self, value=None, **params):
        # log.debug("template: " + template)
        log.debug("path: " + cherrypy.request.path)
        log.debug("checking for path: " + self.path)
        if (self.path == cherrypy.request.path):
            log.debug("they are equal, lets render")
            return widgets.Widget.display(self)
        else:
            log.debug("Not equal, empty!")
            return ""
    
