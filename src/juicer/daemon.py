#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import ConfigParser
import optparse
import os
import signal
import sys
import time

from juicer.server import get_server

__author__ = 'Jason L Connor <jconnor@redhat.com>'
__version__ = '0.0.0'


def parse_cmdline():
    """
    Parse and validate the command line options.
    """
    parser = optparse.OptionParser()
    
    parser.add_option('-c', '--config',
                      action='store',
                      help='configuration file')
    parser.add_option('-F', '--foreground',
                      action='store_true',
                      help=optparse.SUPPRESS_HELP)
    
    parser.set_defaults(config='/etc/juicer.ini',
                        foreground=False)
    
    opts, args = parser.parse_args()
    
    if args:
        parser.error('unknown arguments: %s' % ','.join(args))
    
    opts.config = os.path.normpath(os.path.abspath(opts.config))
    
    if not os.path.exists(opts.config):
        parser.error('no such file: %s' % opts.config)
        
    if not os.access(opts.config, os.R_OK):
        parser.error('cannot read %s, check permissions' % opts.config)
        
    return opts


def parse_config(path):
    """
    Parse the configuration file
    """
    parser = ConfigParser.SafeConfigParser()
    parser.read([path,])
    return parser


def daemonize():
    """
    Double fork the interpreter in order to divorce the program from the shell.
    """
    if os.fork() != 0:
        os.wait()
        os._exit(os.EX_OK)
        
    os.setsid()
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    
    null = os.open(os.devnull, os.O_RDWR)
    os.dup2(null, sys.stdin.fileno())
    os.dup2(null, sys.stdout.fileno())
    os.dup2(null, sys.stderr.fileno())
    os.close(null)
    
    if os.fork() != 0:
        os._exit(os.EX_OK)
        
    while os.getppid() != 1:
        time.sleep(0.25)
        

def run():
    """
    Run the web services daemon.
    """
    opts = parse_cmdline()
    config = parse_config(opts.config)
    if not opts.foreground:
        daemonize()
    server = get_server(config)
    server.server_forever()
    return os.EX_OK

# testing ---------------------------------------------------------------------

if __name__ == '__main__':
    pass