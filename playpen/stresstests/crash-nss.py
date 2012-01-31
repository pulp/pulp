#!/usr/bin/python -tt
import optparse
import pycurl
import sys
from threading import Thread
import time
import traceback

class TestThread(Thread):
    def __init__ (self, threadid, url, cacert, cert, key):
        Thread.__init__(self)
        self.threadid = threadid
        self.stopped = False
        self.url = url
        self.cacert = cacert
        self.cert = cert
        self.key = key

    def protected_fetch(self, url):
        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.CAINFO, self.cacert)
        c.setopt(c.SSLCERT, self.cert)
        if self.key:
            c.setopt(c.SSLKEY, self.key)
        c.setopt(c.SSL_VERIFYPEER, 0)
        c.setopt(c.WRITEDATA, open('/dev/null', 'w'))
        c.perform()
        status = c.getinfo(c.HTTP_CODE)
        return status

    def run(self):
        counter = 0
        while not self.stopped:
            status = self.protected_fetch(url=self.url)
            print "Thread <%s> Iteration <%s> Status = <%s>" % (self.threadid, counter, status)
            counter += 1

def parse_args():
    parser = optparse.OptionParser() 
    parser.add_option('--cacert', action='store', 
                help='CA Certificate')
    parser.add_option('--cert', action='store', 
            help='SSL Certificate')
    parser.add_option('--key', action='store',
            help='SSL Key')
    parser.add_option('--url', action='store',
            help='URL to fetch')
    parser.add_option('--threads', action='store', 
            help='Number of threads', default=50)

    (opts, args) = parser.parse_args()
    return opts, args


RUNNING_THREADS = []
def handle_interrupt(signum, frame):
    for t in RUNNING_THREADS:
        print "Telling thread <%s> to stop" % (t.threadid)
        t.stopped = True
    sys.exit()
import signal
signal.signal(signal.SIGINT, handle_interrupt)

if __name__ == '__main__':
    opts, args = parse_args()
    if not opts.cacert:
        print "No --cacert was specified, this is required"
        sys.exit(1)
    if not opts.cert:
        print "No --cert was specified, this is required"
        sys.exit(1)
    if not opts.key:
        print "Warning: No --key was specified.  Are you sure?"
    if not opts.url:
        print "No --url was specified, this is required"
        sys.exit(1)
    num_threads = int(opts.threads)
    for i in xrange(0, num_threads):
        t = TestThread(i, opts.url, opts.cacert, opts.cert, opts.key) 
        RUNNING_THREADS.append(t)
        print "Created TestThread <%s> to fetch <%s> with cacert = <%s>, cert = <%s>, key = <%s>" % \
                (i, opts.url, opts.cacert, opts.cert, opts.key)
        t.start()
    while 1:
       time.sleep(1)

