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

from suds import WebFault
from suds.serviceproxy import ServiceProxy
from suds.wsdl import WSDL
from suds.property import Property
import logging
import getopt

urlfmt = 'http://localhost:7080/on-on-enterprise-server-ejb./%s?wsdl'

services =\
{ 
   'auth':'SubjectManagerBean', 
   'contentsource':'ContentSourceManagerBean'
}

def get_url(name):
    return urlfmt % services[name]

def login():
    return ServiceProxy(get_url('auth')).login('jonadmin', 'jonadmin')

def sync_content_sources():
    subject = login()
    service = ServiceProxy(get_url('contentsource'))
    pc = service.get_instance('pageControl')
    pc.pageNumber = 0
    pc.pageSize = 0
    for adapter in service.getAllContentSources(subject, pc):
        try:
            print 'synchronizing (%s) ...' % adapter.displayName
            service.synchronizeAndLoadContentSource(subject, adapter.id)
            print '\tfinished'
        except WebFault, fault:
            print '\tfailed: \n', fault
    print 'done'

def usage():
    print "sync-content-sources.py"

 
def main(argv):
    sync_content_sources()
    

if __name__ == "__main__":
    main(sys.argv[1:])

