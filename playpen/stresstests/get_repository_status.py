#!/usr/bin/python -tt
import base64
import optparse
import pycurl
import sys
import thread
import time
import traceback
from threading import Thread

class TestThread(Thread):
    def __init__ (self, threadid, url, cacert, cert, key, username, password):
        Thread.__init__(self)
        self.threadid = threadid
        self.stopped = False
        self.url = url
        self.cacert = cacert
        self.cert = cert
        self.key = key
        self.username = username
        self.password = password

    def get_header(self, username, password):
        raw = ':'.join((username, password))
        encoded = base64.encodestring(raw)[:-1]
        return "Basic " + encoded

    def protected_fetch(self, url):
        c = pycurl.Curl()
        c.setopt(c.URL, url)
        if self.cacert:
            c.setopt(c.CAINFO, self.cacert)
        if self.cert:
            c.setopt(c.SSLCERT, self.cert)
        if self.key:
            c.setopt(c.SSLKEY, self.key)
        if self.username and self.password:
            auth = self.get_header(self.username, self.password)
            c.setopt(pycurl.HTTPHEADER, ["Authorization: %s" % auth])
        c.setopt(c.SSL_VERIFYPEER, 0)
        c.setopt(c.WRITEDATA, open('/dev/null', 'w'))
        c.perform()
        status = c.getinfo(c.HTTP_CODE)
        return status

    def run(self):
        counter = 0
        while not self.stopped:
            start = time.time()
            status = self.protected_fetch(url=self.url)
            end = time.time()
            print "%s %s Status <%s> Thread <%s> Iteration <%s> took %s seconds" % (time.ctime(), self.url, status, self.threadid, counter, end-start)
            counter += 1
            if status != 200:
                print "Bad Status: %s at %s, call took %s seconds" % (status, time.ctime(), end-start)
                stop_threads()
                sys.exit(1)

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
            help='Number of threads', default=5)
    parser.add_option('--username', action='store',
            help='User name')
    parser.add_option('--password', action='store',
            help='User password')

    (opts, args) = parser.parse_args()
    return opts, args

RUNNING_THREADS = []

def stop_threads():
    print "Intentionally stopping all threads"
    for t in RUNNING_THREADS:
        #print "Telling thread <%s> to stop" % (t.threadid)
        t.stopped = True
    thread.interrupt_main()

def handle_interrupt(signum, frame):
    stop_threads()
    sys.exit(0)

import signal
signal.signal(signal.SIGINT, handle_interrupt)

if __name__ == '__main__':
    opts, args = parse_args()
    if not opts.url:
        print "No --url was specified, this is required"
        sys.exit(1)
    num_threads = int(opts.threads)
    for i in xrange(0, num_threads):
        t = TestThread(i, opts.url, opts.cacert, opts.cert, opts.key, opts.username, opts.password) 
        RUNNING_THREADS.append(t)
        print "Created TestThread <%s> to fetch <%s> with cacert = <%s>, cert = <%s>, key = <%s>" % \
                (i, opts.url, opts.cacert, opts.cert, opts.key)
    for t in RUNNING_THREADS:
        t.start()
    while 1:
       time.sleep(1)

