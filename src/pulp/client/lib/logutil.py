#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import os
import sys
import logging
from logging import root, Formatter
from logging.handlers import RotatingFileHandler

USRDIR = '~/.pulp'
LOGDIR = '/var/log/pulp'
LOGFILE = 'client.log'

TIME = '%(asctime)s'
LEVEL = ' [%(levelname)s]'
THREAD = '[%(threadName)s]'
FUNCTION = ' %(funcName)s()'
FILE = ' @ %(filename)s'
LINE = ':%(lineno)d'
MSG = ' - %(message)s'

if sys.version_info < (2,5):
    FUNCTION = ''

FMT = \
    ''.join((TIME,
            LEVEL,
            THREAD,
            FUNCTION,
            FILE,
            LINE,
            MSG,))

Response_FMT = \
    ''.join((TIME,
            FILE,
            LINE,
            MSG,))

handler = None

def __logdir():
    if os.getuid() == 0:
        return LOGDIR
    else:
        return os.path.expanduser(USRDIR)

def getLogger(name):
    global handler
    logdir = __logdir()
    if not os.path.exists(logdir):
        os.mkdir(logdir)
    if handler is None:
        path = os.path.join(logdir, LOGFILE)
        handler = RotatingFileHandler(path, maxBytes=0x100000, backupCount=5)
        handler.setFormatter(Formatter(FMT))
        root.setLevel(logging.INFO)
        root.addHandler(handler)
    log = logging.getLogger(name)
    return log

def getResponseLogger(name, api_response_log):
    path = api_response_log
    response_handler = RotatingFileHandler(path, maxBytes=0x100000, backupCount=5)
    response_handler.setFormatter(Formatter(Response_FMT))
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    log.addHandler(response_handler)
    return log
