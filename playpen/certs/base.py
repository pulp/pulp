#!/usr/bin/env python

import ConfigParser
import os
import shlex
import socket
import subprocess
import sys
from optparse import OptionParser

def check_dirs(p):
    if not os.path.exists(os.path.dirname(p)):
        os.makedirs(os.path.dirname(p))

def update_openssl_config(template_file, output_name, index=None, crlnumber=None):
    if not os.path.exists(template_file):
        print "Unable to find template file for openssl configuration: %s" % (template_file)
        return False
    check_dirs(output_name)
    template = open(template_file, "r").read()
    template = template.replace("REPLACE_CRL_DATABASE_FILE", index)
    template = template.replace("REPLACE_CRL_NUMBER_FILE", crlnumber)
    out_file = open(output_name, "w").write(template)
    return True

def run_command(cmd, verbose=True):
    if verbose:
        print "Running: %s" % (cmd)
    if isinstance(cmd, str):
        cmd = shlex.split(cmd.encode('ascii', 'ignore'))
    handle = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out_msg, err_msg = handle.communicate(None)
    if handle.returncode != 0:
        print "Error running: %s" % (cmd)
        print "stdout:\n%s" % (out_msg)
        print "stderr:\n%s" % (err_msg)
        return False
    return True, out_msg, err_msg

def get_config(filename='config_pulp_certs.cfg', section='certs'):
    config = ConfigParser.ConfigParser()
    config.read(filename)
    cfg = {}
    for item,value in config.items(section):
        cfg[item] = value
    return cfg

def get_parser(config=None, parser=None, description=None, limit_options=None):
    if not config:
        config = get_config()
    if not parser:
        if not description:
            description="Helper utility to create certs for repository authentication"
        parser = OptionParser(description=description)
    keys = config.keys()
    keys.sort() # want --help to list options in order
    for item in keys:
        if limit_options:
            if item not in limit_options:
                continue
        value = config[item]
        parser.add_option('--%s' % (item), action='store', help="Default value: %s" % value, default=value)
    return parser

def add_hostname_option(parser, hostname=None):
    if not hostname:
        hostname = socket.gethostname()
    parser.add_option('--hostname', action='store', 
            help="Default value: %s" % (hostname), default=hostname)
    return parser
