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
import sys
from logging import getLogger

log = getLogger(__name__)


class PluginLoader:
    """
    Agent plugins loader.
    """

    ROOT = '/var/lib/pulp'
    PLUGINS = 'agentplugins'

    @classmethod
    def abspath(cls):
        return os.path.join(cls.ROOT, cls.PLUGINS)

    def __init__(self):
        path = self.abspath()
        if os.path.exists(path):
            return
        os.makedirs(path)
        pkg = os.path.join(path, '__init__.py')
        f = open(pkg, 'w')
        f.close()

    def load(self):
        """
        Load the plugins.
        """
        sys.path.append(self.ROOT)
        path = self.abspath()
        for fn in os.listdir(path):
            if fn.startswith('__'):
                continue
            if not fn.endswith('.py'):
                continue
            self.__import(fn)

    def __import(self, fn):
        """
        Import a module by file name.
        @param fn: The module file name.
        @type fn: str
        """
        mod = fn.rsplit('.', 1)[0]
        imp = '%s.%s' % (self.PLUGINS, mod)
        try:
            __import__(imp)
            log.info('plugin "%s", imported', imp)
        except:
            log.error('plugin "%s", import failed', imp, exc_info=True)
