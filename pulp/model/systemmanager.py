from pulp.model.base import PageControl
from pulp.model.pulpserviceproxy import PulpServiceProxy 
from suds.property import Property
import logging

class SystemManager(object):
    
    def __init__(self):
        self.service = PulpServiceProxy().getServiceProxy('ResourceManagerBean')
        
        
    def list_systems(self, subject):
        systems = self.service.findResourceComposites(subject, 'PLATFORM',\
                                               'Linux', -1, None, PageControl())
        for s in systems:
            s.name = s.resource.name
            s.description = s.resource.description
            s.id = s.resource.id
            
        return systems
        