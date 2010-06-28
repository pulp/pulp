#!/usr/bin/python

from threading import Thread
import urllib
import time
import pycurl
import json
import cStringIO
import gzip
import StringIO
import signal
import xml.dom.minidom
import sys


class WorkerThread(Thread):
    def __init__(self, base_url, path):
        Thread.__init__(self)
        self.base_url = base_url
        self.paths = path
        self._stop = False
    
    def stop(self):
        print "Stop called."
        self._stop = True

    def run(self):
        while(True):
            for p in self.paths:
                if (self._stop):
                    print "Stopping, wait a few please!"
                    break
                url = self.base_url + p
                print "Base API url: [%s]" % url
                output = fetchUrl(url)
                jsout = json.loads(output)
                ids = []
                for row in jsout:
                    # print "ID: %s" % row['id']
                    ids.append(row['id'])
                print "Found all objects under [%s], fetching actual objects" % url
                suburl = ""
                for id in ids:
                    suburl = url + id + "/"
                    fetchUrl(suburl)
                print "Done listing all objects under [%s]" % url
            if (self._stop):
                print "Stopping, wait a few please!"
                break

def running(threads):
    working = 0
    for t in threads:
        if (t.isAlive()):
            working += 1
    return (working > 0)

def waitForThreads(threads):
    while (running(threads)):
        print("Wait 2.  check again")
        time.sleep(2)
    


def fetchUrl(url):
    response = cStringIO.StringIO()
    
    c = pycurl.Curl()
    c.setopt(pycurl.VERBOSE,0)
    c.setopt(pycurl.URL, str(url))
    c.setopt(c.WRITEFUNCTION, response.write)
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    out = c.perform()
    # print c.getinfo(pycurl.HTTP_CODE), c.getinfo(pycurl.EFFECTIVE_URL)
    # print "out: %s" % out
    c.close()

    return response.getvalue()


def main(base_url, threadcount): 
    threads = []
    def handleKeyboardInterrupt(signalNumer, frame):
        for t in threads:
            t.stop()

    signal.signal(signal.SIGINT, handleKeyboardInterrupt)


    paths = ['/packages/', '/consumers/', '/repositories/']
    threads = []
    for i in range(int(threadcount)):
        print "starting thread: %s" % i
        thread = WorkerThread(base_url, paths)
        thread.start()
        threads.append(thread)

    waitForThreads(threads)


if __name__ == "__main__":
    if (len(sys.argv) < 3):
        sys.exit("Usage: webservice_loader.py <base-url> <num threads>")
    base_url = sys.argv[1]
    threadcount = sys.argv[2]
    print("Using base_url [%s] with [%s] threads" % (base_url, threadcount))
    main(base_url, threadcount)


