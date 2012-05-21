#!/usr/bin/env python
import os
import sys
import time
import hashlib
import socket

# from apache config
AuthTokenSecret = "secret" 
AuthTokenPrefix = "/downloads/"     
hex_time =  hex(int(time.time()))[2:] 
server_url = "http://%s" % socket.gethostname()

def build_url(filename):
    def token_generator(filename):
        token = hashlib.md5(''.join([AuthTokenSecret, '/', filename, hex_time])).hexdigest()
        return token
    token = token_generator(filename)
    url = ''.join([server_url, AuthTokenPrefix, '/'.join([token, hex_time, filename])])
    return url


if __name__=='__main__':
    if len(sys.argv) != 2:
        print("python mod_auth_token_prototype.py <filename>")
        sys.exit(0)
    print build_url(sys.argv[1])
