from turbogears import widgets
import cherrypy
import logging
import turbogears
import xml.dom.minidom

log = logging.getLogger("pulp.navbar")

def buildnav(xmlfile):
    nb = Nav(xmlfile=xmlfile, template="pulp.templates.nav")
    return nb.display()

def add_custom_stdvars(vars):
    return vars.update({"buildnav": buildnav})

turbogears.view.variable_providers.append(add_custom_stdvars)

class Nav(widgets.Widget):
    def __init__(self, *args, **kw):
        super(Nav,self).__init__(*args, **kw)
        self.xmlfile = kw['xmlfile']

    def display(self, value=None, **params):
        f = open(self.xmlfile, mode="r")
        log.debug("file: " + self.xmlfile)
        #f = open(file, mode="r")
        doc = xml.dom.minidom.parse(f)
        log.debug("path: " + cherrypy.request.path)
            
        tabs = doc.getElementsByTagName("tab")
        tablist = []
        for t in tabs:
            nt = NavTab(t.getAttribute("name"), t.getAttribute("url"), 
                cherrypy.request.path == t.getAttribute("url"))
            tablist.append(nt)
        return widgets.Widget.display(self, tabs=tablist)
    
    

class NavTab:
    def __init__(self, name, url, active):
        self.name = name
        self.url = url
        self.active = active
