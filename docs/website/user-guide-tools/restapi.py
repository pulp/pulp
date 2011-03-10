#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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

import inspect
import os
import re
import sys
import traceback
import types
from optparse import OptionParser

# -----------------------------------------------------------------------------

def parse_args(args=sys.argv[1:]):
    about = "generate trac wiki files for pulp's rest api"
    parser = OptionParser(description=about)
    parser.add_option('-o', '--out', dest='out', default='.',
                      help='output directory for wiki files')
    parser.add_option('-s', '--src', dest='src', default=None,
                      help='source directory')
    opts, args = parser.parse_args(args)
    return opts

# -----------------------------------------------------------------------------

_parent_module = 'pulp.server.webservices.controllers'

_module_names = ('audit', 'cds', 'consumergroups', 'consumers', 'content',
                 'distribution', 'errata', 'filters', 'orphaned', 'packages',
                 'permissions', 'repositories', 'roles', 'services', 'users')


def _import_module(name):
    module = __import__(name)
    for part in name.split('.')[1:]:
        module = getattr(module, part)
    return module


def import_base_class():
    module = _import_module('.'.join((_parent_module, 'base')))
    return getattr(module, 'JSONController')


def import_modules():
    modules = []
    for name in _module_names:
        modules.append(_import_module('.'.join((_parent_module, name))))
    return modules

# -----------------------------------------------------------------------------

doc_marker = re.compile(r'\[\[wiki\]\]', re.I)


def process_doc_string(doc):
    doc_string, wiki_doc = doc_marker.split(doc)
    return wiki_doc


def gen_docs_for_class(cls):
    docs = ''
    for attr in cls.__dict__.values():
        if not inspect.isroutine(attr):
            continue
        doc = getattr(attr, '__doc__', None)
        name = getattr(attr, '__name__', 'Unnamed')
        if doc is None:
            print >> sys.stderr, 'skipped %s: no doc string' % name
            continue
        if not doc_marker.search(doc):
            print >> sys.stderr, 'skipped %s: no wiki formatting' % name
            continue
        docs += process_doc_string(doc)
    return docs


def gen_docs_for_module(module):
    docs = ''
    cls = import_base_class()
    for name, attr in module.__dict__.items():
        print name, type(attr)
        if not (type(attr) == types.TypeType and issubclass(attr, cls)):
            continue
        docs += gen_docs_for_class(attr)
    return docs


def write_docs_for_module(name, docs):
    print name
    print docs

# -----------------------------------------------------------------------------

def main():
    opts = parse_args()
    sys.path.insert(0, opts.src)
    for module in import_modules():
        try:
            docs = gen_docs_for_module(module)
            write_docs_for_module(module.__name__, docs)
        except Exception, e:
            print >> sys.stderr, 'doc generation for %s failed' % module.__name__
            print >> sys.stderr, ''.join(traceback.format_exception(*sys.exc_info()))
            print >> sys.stderr, str(e)
            continue
    return os.EX_OK


if __name__ == '__main__':
    sys.exit(main())
