# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )
import sys
sys.path.append("..")

from suds import *
from suds.serviceproxy import ServiceProxy
from suds.schema import Schema
from suds.propertyreader import DocumentReader, Hint
from suds.property import Property
from suds.wsdl import WSDL


urlfmt = 'http://localhost:7080/on-on-enterprise-server-ejb./%s?wsdl'

services = \
{ 
    'test':'WebServiceTestBean', 
    'auth':'SubjectManagerBean', 
    'resources':'ResourceManagerBean',
    'perspectives':'PerspectiveManagerBean',
    'content':'ContentManagerBean',
    'contentsource':'ContentSourceManagerBean'
}

def get_url(name):
    return urlfmt % services[name]

class Test:
    
    def basic_test(self):
        
        #
        # create a service proxy using the wsdl.
        #
        service = ServiceProxy(get_url('test'))
        
        #
        # print the service (introspection)
        #
        print service
        
        #
        # create a name object using the wsdl
        #
        name = service.get_instance('name')
        name.first = 'jeff'
        name.last = 'ortel'
        
        #
        # create a phone object using the wsdl
        #
        phoneA = service.get_instance('phone')
        phoneA.npa = 410
        phoneA.nxx = 822
        phoneA.number = 5138

        phoneB = service.get_instance('phone')
        phoneB.npa = 919
        phoneB.nxx = 606
        phoneB.number = 4406
        
        #
        # create a person object using the wsdl
        #
        person = service.get_instance('person')
        
        #
        # inspect empty person
        #
        print '{empty} person=\n%s' % person
        
        person.name = name
        person.age = 43
        person.phone.append(phoneA)
        person.phone.append(phoneB)
        
        #
        # inspect person
        #
        print 'person=\n%s' % person
        
        #
        # add the person (using the webservice)
        #
        print 'addPersion()'
        result = service.addPerson(person)
        print '\nreply(\n%s\n)\n' % str(result)
        
        #
        # create a new name object used to update the person
        #
        newname = service.get_instance('name')
        newname.first = 'Todd'
        newname.last = 'Sanders'
        
        #
        # update the person's name (using the webservice) and print return person object
        #
        print 'updatePersion()'
        result = service.updatePerson(person, newname)
        print '\nreply(\n%s\n)\n' % str(result)
        
        
        #
        # invoke the echo service
        #
        print 'echo()'
        result = service.echo('this is cool')
        print '\nreply( %s )\n' % str(result)
        
        #
        # invoke the hello service
        #
        print 'hello()'
        result = service.hello()
        print '\nreply( %s )\n' % str(result)
        
        #
        # invoke the testVoid service
        #
        try:
            print 'testVoid()'
            result = service.testVoid()
            print '\nreply( %s )\n' % str(result)
        except Exception, e:
            print e
        
        #
        # test exceptions
        #
        try:
            print 'testExceptions()'
            result = service.testExceptions()
            print '\nreply( %s )\n' % str(result)
        except Exception, e:
            print e
            
    def auth_test(self):
        
        service = ServiceProxy(get_url('auth'))
        
        #
        # print the service (introspection)
        #
        print service
            
        #
        # login
        #
        print 'login()'
        subject = service.login('jonadmin', 'jonadmin')
        print '\nreply(\n%s\n)\n' % str(subject)
        
        #
        # create page control and get all subjects
        #
        pc = service.get_instance('pageControl')
        pc.pageNumber = 0
        pc.pageSize = 0
        
        print 'getAllSubjects()'
        users = service.getAllSubjects(pc)
        print 'Reply:\n(\n%s\n)\n' % str(users)
        
        #
        # get user preferences
        #
        print 'loadUserConfiguration()'
        prefs = service.loadUserConfiguration(subject.id)
        print 'Reply:\n(\n%s\n)\n' % str(prefs)
        

    def resource_test(self):
        
        print 'testing resources (service) ...'
        
        #
        # create a service proxy using the wsdl.
        #
        service = ServiceProxy(get_url('resources'))

        #
        # print the service (introspection)
        #
        print service

        #
        # login
        #
        print 'login()'
        subject = ServiceProxy(get_url('auth')).login('jonadmin', 'jonadmin')
        print '\nreply(\n%s\n)\n' % str(subject)
        
        #
        # create page control and get all subjects
        #
        pc = service.get_instance('pageControl')
        pc.pageNumber = 0
        pc.pageSize = 0
        
        #
        # get enumerations
        #
        resourceCategory = service.get_enum('resourceCategory')
        print 'Enumeration (resourceCategory):\n%s' % resourceCategory
        
        
        #
        # get resource by category
        #
        print 'getResourcesByCategory()'
        platforms = service.getResourcesByCategory(subject, resourceCategory.PLATFORM, 'COMMITTED', pc)
        print 'Reply:\n(\n%s\n)\n' % str(platforms)
        
        #
        # get resource tree
        #
        for p in platforms:
            print 'getResourcesTree()'
            tree = service.getResourceTree(p.id)
            print 'Reply:\n(\n%s\n)\n' % str(tree)
            
    def perspectives_test(self):
        
        print 'testing perspectives (service) ...'
        
        #
        # create a service proxy using the wsdl.
        #
        service = ServiceProxy(get_url('perspectives'))

        #
        # print the service (introspection)
        #
        print service

        #
        # login
        #
        print 'login()'
        subject = ServiceProxy(get_url('auth')).login('jonadmin', 'jonadmin')
        print "subject: ", str(subject)

        #
        # get all perspectives
        #
        print 'getPerspective()'
        perspectives = service.getPerspective("content")
        print 'perspectives: ', str(perspectives)
        
        print 'getAllPerspective()'
        perspectives = service.getAllPerspectives()
        print 'perspectives: ', str(perspectives)
        
    def contentsource_test(self):
        
        print 'testing content source (service) ...'
        
        #
        # create a service proxy using the wsdl.
        #
        service = ServiceProxy(get_url('contentsource'))

        #
        # print the service (introspection)
        #
        print service
        
        configuration = service.get_instance('configuration')
        print configuration
        entry = service.get_instance('configuration.properties.entry')
        simple = service.get_instance('propertySimple')
        entry.key = 'url'
        simple.name = 'url'
        simple.stringValue = 'http://download.skype.com/linux/repos/fedora/updates/i586'
        entry.value = simple
        configuration.properties.entry.append(entry)
        configuration.notes = 'SkipeAdapter'
        configuration.version = 1234
        print configuration
        
        name = 'SkipeAdapter'
        displayName = 'Skipe Adapter'
        description = 'The skipe adapter'
        type = 'YumSource'

        #
        # login
        #
        print 'login()'
        subject = ServiceProxy(get_url('auth')).login('jonadmin', 'jonadmin')
        print "subject: ", str(subject)

        #
        # get all perspectives
        #
        try:
            print 'createContentSource()'
            result = service.createContentSource(subject, name, displayName, description, type, configuration, False)
            print 'createContentSource: ', str(result)
        except Exception, e:
            print e
        
    def content_source_channel_test(self):
        service = ServiceProxy(get_url('contentsource'))
        subject = ServiceProxy(get_url('auth')).login('jonadmin', 'jonadmin')
        ids = [50,3050,550]
        print "Adding sources to channel"
        service.addContentSourcesToChannel(subject, 51, ids)
        

def test1():
    wsdl = WSDL(get_url('test'))
    schema = Schema(wsdl.definitions_schema())
    print schema.build('person')
    
def test2():
    wsdl = WSDL(get_url('contentsource'))
    schema = Schema(wsdl.definitions_schema())
    print schema.build('configuration')
    
def test3():
    wsdl = WSDL(get_url('contentsource'))
    schema = Schema(wsdl.definitions_schema())
    #print schema.build('property')
    #print schema.build('configuration.properties.entry')
    print schema.build('propertySimple')

def test4():
    hint = Hint()
    hint.sequences = ('/root/test',)
    xml = '<root><test/></root>'
    reader = DocumentReader(hint=hint)
    d = reader.read(string=xml)
    print d
    
def test5():
    wsdl = WSDL(get_url('auth'))
    schema = Schema(wsdl.definitions_schema())
    hint = schema.get_hint('loginResponse')
    print 'hint_____________________'
    for p in hint.sequences:
        print p
    hint = schema.get_hint('loginResponse')
    print 'hint_____________________'
    for p in hint.sequences:
        print p
        
if __name__ == '__main__':
    #test5()
    #test3()
    test = Test()
    #test.basic_test()
    #test.auth_test()
    #test.resource_test()
    #test.perspectives_test()
    #test.contentsource_test()
    test.content_source_channel_test()