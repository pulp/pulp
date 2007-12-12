from suds.property import Property
from pulp.model.pulpserviceproxy import PulpServiceProxy 
import logging

class ContentManager(object):
    
    def __init__(self):
        self.service = PulpServiceProxy().getServiceProxy('ContentSourceManagerBean')
    
    def get_content_source(self, subject, id):
        source = self.service.getContentSource(id)
        return source
    
    def list_all_content_sources(self, subject):
        sources = self.service.getAllContentSources(subject)
        for s in sources:
            s.type = s.contentSourceType.displayName
            print "Type: ", s.type
        return sources
        
    def update_content_source(self,                                
                              subject,
                              id, 
                              name, 
                              displayName, 
                              description, 
                              lazyLoad,
                              url):
                
        source = self.service.getContentSource(id)
        print "we got a content source: ", source.id
        source.name = name
        source.displayName = displayName
        source.description = description
        source.lazyLoad = lazyLoad
        source.configuration.properties.entry.value.stringValue = url      
        self.service.updateContentSource(subject, source)
        return id

    def create_content_source(self, subject, name, displayName, description, lazyLoad, url):

        configuration = self.service.get_instance('configuration')
        entry = self.service.get_instance('configuration.properties.entry')
        simple = self.service.get_instance('propertySimple')
        entry.key = 'url'
        simple.name = 'url'
        simple.stringValue = url
        entry.value = simple
        configuration.properties.entry.append(entry)
        configuration.notes = name, ' configuration entry'
        
        #lazy = str(lazyLoad == 'on').lower()
        lazy = lazyLoad.lower()
        
        source = self.service.createContentSource(subject, 
                                                   name,
                                                   displayName,
                                                   description,
                                                   "YumSource",
                                                   configuration,
                                                   lazy)
        print "we got a content source: ", source.id
        
        return source.id
                
    
