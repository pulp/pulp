#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

import inspect
import os
import re
import sys
import traceback
from optparse import OptionParser

try:
    from pulp.server.webservices.controllers import (
        audit, base, cds, consumergroups, consumers, content, distribution,
        errata, orphaned, packages, permissions, repositories, roles, services,
        users,)
except ImportError:
    print >> sys.stderr, 'this script needs to run from the development src directory'
    print >> sys.stderr, os.getcwd()
    raise
    sys.exit(os.EX_UNAVAILABLE)


modules = (audit, cds, consumergroups, consumers, countent, distribution,
           errata, orphaned, packages, permissions, repositories, roles,
           services, users)


doc_marker = re.compile(r'\[\[wiki\]\]', re.I)

# -----------------------------------------------------------------------------

def parse_args(args=sys.argv[1:]):
    about = "generate trac wiki files for pulp's rest api"
    parser = OptionParser(about=about)
    parser.add_option('-d', '--dir', dest='dir', default='.',
                      help='output directory for wiki files')


def process_doc_string(doc):
    doc_string, wiki_doc = doc_marker.split(doc)
    return wiki_doc


def gen_docs_for_class(cls):
    docs = ''
    for attr in cls.__dict__.values():
        if not inspect.isroutine(attr):
            continue
        doc = getattr(attr, '__doc__', None)
        if doc is None:
            print >> sys.stderr, 'skipped %s: no doc string' % attr.__name__
            continue
        if not doc_marker.search(doc):
            print >> sys.stderr, 'skipped %s: no wiki formatting' % attr.__name__
            continue
        docs += process_doc_string(doc)
    return docs


def gen_docs_for_module(module):
    docs = ''
    for attr in module.__dict__.values():
        if not issubclass(attr, base.JSONController):
            continue
        docs += gen_docs_for_class(attr)
    return docs


def write_docs_for_module(name, docs):
    print name
    print docs


def main():
    for m in modules:
        try:
            docs = gen_docs_for_module(m)
            write_docs_for_module(m.__name__, docs)
        except Exception, e:
            print >> sys.stderr, 'doc generation for %s failed' % m.__name__
            print >> sys.stderr, ''.join(traceback.format_exception(*sys.exc_info()))
            print >> sys.stderr, str(e)
            continue
    return os.EX_OK

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    sys.exit(main())
