#!/usr/bin/python

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

from suds.serviceproxy import ServiceProxy
import logging
import getopt
from suds.wsdl import WSDL
from suds.property import Property

urlfmt = 'http://localhost:7080/on-on-enterprise-server-ejb./%s?wsdl'

services = { 
    'test':'WebServiceTestBean', 
    'auth':'SubjectManagerBean', 
    'resources':'ResourceManagerBean',
    'perspectives':'PerspectiveManagerBean' ,
    'content':'ContentSourceManagerBean'
}

def get_url(name):
    return urlfmt % services[name]

def create_yum_content_source(name, url):
    service = ServiceProxy(get_url('content'))
    subject = ServiceProxy(get_url('auth')).login('jonadmin', 'jonadmin')
    from suds.property import Property
    

    configuration = service.get_instance('configuration')
    entry = service.get_instance('configuration.properties.entry')
    simple = service.get_instance('propertySimple')
    entry.key = 'url'
    simple.name = 'url'
    simple.stringValue = url
    entry.value = simple
    configuration.properties.entry.append(entry)
    configuration.notes = name, ' configuration entry'

    source = service.createContentSource(subject, 
                                               name,
                                               name,
                                               name,
                                               "YumSource",
                                               configuration,
                                               False)

def usage():
    print "create-content-source.py -n some name -u http://somehost.redhat.com"

 
def main(argv):
    name = None
    url = None
    
    try:
        opts, args = getopt.getopt(argv, "n:u:", ["name=", "url="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-n", "-name", "--name"):
            name = arg
        elif opt in ("-u", "-url", "--url"):
            url = arg
    if ((name is None) or (url is None)):
        usage()
        sys.exit(2)
    create_yum_content_source(name, url)
    print "Content Source Created."
    

if __name__ == "__main__":
    main(sys.argv[1:])

