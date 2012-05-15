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

from pulp.gc_client.consumer.config import ConsumerConfig
from pulp.gc_client.consumer.credentials import ConsumerBundle
from pulp.gc_client.api.server import PulpConnection
from pulp.gc_client.api.bindings import Bindings


class Connection(PulpConnection):
    """
    Configured I{connection}.
    """
    
    def __init__(self):
        cfg = ConsumerConfig()
        PulpConnection.__init__(
            self,
            cfg.server.host,
            int(cfg.server.port),
            cert_filename=ConsumerBundle.path())
        

class PulpBindings(Bindings):
    """
    Configured pulp (rest) bindings.
    """
    
    def __init__(self):
        Bindings.__init__(self, Connection())
