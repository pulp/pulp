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

import logging
from logging import Formatter
from logging.handlers import RotatingFileHandler

GRINDER_LOG_FILENAME = "./log-grinder.out"
LOG = logging.getLogger("grinder")
G_LOGGER_LOADED = False
def setup(verbose):
    global G_LOGGER_LOADED
    # Only load logger once
    if G_LOGGER_LOADED:
        return
    logging.basicConfig(filename=GRINDER_LOG_FILENAME, level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M', filemode='w')
    console = logging.StreamHandler()
    if verbose:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    formatter = Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    handler = RotatingFileHandler(GRINDER_LOG_FILENAME, maxBytes=0x100000, \
                                  backupCount=5)
    handler.setFormatter(formatter)
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    G_LOGGER_LOADED = True
