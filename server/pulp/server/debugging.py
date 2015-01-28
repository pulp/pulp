# -*- coding: utf-8 -*-

import atexit
import os
import Queue
import sys
import threading
import traceback


FLAGFILE = '/var/log/pulp/stacktrace-dump'


class StacktraceDumper(object):

    def __init__(self, flag_file=FLAGFILE, interval=1.0):
        self.flag_file = flag_file
        self.interval = interval
        self.queue = Queue.Queue()
        self.lock = threading.Lock()
        self.thread = None
        self.mtime = None
        try:
            self.mtime = os.path.getmtime(self.flag_file)
        except:
            pass

    def _stacktraces(self):
        # fetch the current stack traces for all active threads
        code = []
        for thread_id, stack in sys._current_frames().items():
            code.append("\n# ProcessId: %s" % os.getpid())
            code.append("# ThreadID: %s" % thread_id)
            for filename, lineno, name, line in traceback.extract_stack(stack):
                code.append('File: "%s", line %d, in %s' %
                            (filename, lineno, name))
                if line:
                    code.append("  %s" % (line.strip()))
        # actually "prints" to the apache error log
        for line in code:
            print >> sys.stderr, line

    def _monitor(self):
        # monitor the flag file, if it's mtime has changed, dump stack traces
        while True:
            try:
                current = os.path.getmtime(self.flag_file)
            except:
                current = None
            if current != self.mtime:
                self.mtime = current
                self._stacktraces()
            try:
                return self.queue.get(timeout=self.interval)
            except:
                pass

    def start(self):
        atexit.register(self.exit)
        self.thread = threading.Thread(target=self._monitor)
        self.thread.setDaemon(True)
        self.thread.start()

    def exit(self):
        try:
            self.queue.put(True)
        except:
            pass
        self.thread.join()
