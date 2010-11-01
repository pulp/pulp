#
# Copyright (c) 2010 Red Hat, Inc.
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
#

import os
import logging
from logging import root, Formatter
from logging.handlers import RotatingFileHandler

USRDIR = '~/.pulp'
LOGDIR = '/var/log/pulp'
LOGFILE = 'client.log'

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
        fmt = '%(asctime)s [%(levelname)s][%(threadName)s] %(funcName)s() @ %(filename)s:%(lineno)d - %(message)s'
        handler = RotatingFileHandler(path, maxBytes=0x100000, backupCount=5)
        handler.setFormatter(Formatter(fmt))
        root.setLevel(logging.INFO)
        root.addHandler(handler)
    log = logging.getLogger(name)
    return log
