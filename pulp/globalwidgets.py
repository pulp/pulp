from perspectives import PerspectiveManager
from turbogears import widgets
import cherrypy
import logging
import xml.dom.minidom

log = logging.getLogger("pulp.globalwidgets")

class GlobalWidget(widgets.Widget):
    template="pulp.templates.global-widget"
     
class NavBar(widgets.Widget):
    template="pulp.templates.nav"

    def display(self, value=None, **params):
        pm = PerspectiveManager()
        perspective = pm.get_current_perspective() 
        xmlfile = "pulp/perspectives/nav/" + perspective.name + "-nav.xml"
        f = open(xmlfile, mode="r")
        log.debug("file: " + xmlfile)
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
    

class PerspectiveList(widgets.Widget):
    template="pulp.templates.perspective-list"

class SideBar(widgets.Widget):
    template="pulp.templates.overview-sidebar"

class NavTab:
    def __init__(self, name, url, active):
        self.name = name
        self.url = url
        self.active = active
