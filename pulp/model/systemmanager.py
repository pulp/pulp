from pulp.model.base import get_page_control
from pulp.model.pulpserviceproxy import PulpServiceProxy 
import logging

class SystemManager(object):
    
    def __init__(self):
        self.service = PulpServiceProxy().getServiceProxy('ResourceManagerBean')
        
        
    def list_systems(self, subject):
        systems = self.service.findResourceComposites(subject, 'PLATFORM',\
                                        'Linux', -1, None, get_page_control())
        #massage the data for datagrid
        for s in systems:
            s.name = s.resource.name
            s.description = s.resource.description
            s.id = s.resource.id
            
        return systems
        
