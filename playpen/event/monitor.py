#!/usr/bin/python

from pulp.server.event.consumer import EventConsumer
from logging import basicConfig

class Monitor(EventConsumer):
    def raised(self, subject, event):
        print '(%s) %s' % (subject, event)

if __name__ == '__main__':
    basicConfig()
    m = Monitor()
    m.start()
    print 'started ...'
    m.join()
