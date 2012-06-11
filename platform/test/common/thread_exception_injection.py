#!/usr/bin/python
import ctypes
import sys
import threading
import time
import traceback


def thread_main():
    try:
        while True:
            #time.sleep(0.05)
            pass
    except Exception, e:
        pass


def inject_exception(thread):
    tid = ctypes.c_long(thread.ident)
    excptr = ctypes.py_object(Exception)
    return ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, excptr)


def main():
    thread = threading.Thread(target=thread_main)
    #thread.daemon = True
    thread.start()
    time.sleep(0.05)
    num = inject_exception(thread)
    time.sleep(0.05)
    return num


if __name__ == '__main__':
    print main()
