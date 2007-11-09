from turbogears import widgets
import cherrypy
import logging
import turbogears
import xml.dom.minidom

log = logging.getLogger("pulp.perspective")

class PerspectiveSummaryWidget(widgets.Widget):
    template = "pulp.templates.perspective-summary"

    def __init__(self, *args, **kw):
        super(PerspectiveSummaryWidget,self).__init__(*args, **kw)
        self.summaries = kw['summaries']

    def display(self, value=None, **params):
        return widgets.Widget.display(self, summaries=self.summaries)        

class PerspectiveSummary:
    def __init__(self, title, type_one, type_two):
        self.title = title
        self.type_one = type_one
        self.type_two = type_two
    