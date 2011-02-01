# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

import os
import re


_mod_regex = re.compile(r'(!__init__)\.py$')


def _import_module(name):
    mod = __import__(name)
    for sub in name.split('.')[1:]:
        mod = getattr(mod, sub, None)
        if mod is None:
            raise RuntimeError('cannot import module %s: module not found' %
                               name)
    return mod


def _get_migration_module_names():
    #package = 'pulp.server.db.migrate.versions'
    package = __name__
    mod_dir = os.path.dirname(__file__)
    names = ['.'.join((packge, n.rsplit('.', 1)))
             for n in os.listdir(mod_dir)
             if _mod_regex.match(n)]
    return names


def get_migration_modules():
    modules = []
    for name in _get_migration_module_names():
        mod = _import_module(name)
        for attr in ('migrate', 'version'):
            if not hasattr(mod, attr):
                raise RuntimeError('module %s is missing %s attribute' %
                                   (name, attr))
            modules.append(mod)
    return sorted(modules, cmp=lambda x,y: cmp(x.version, y.version))
