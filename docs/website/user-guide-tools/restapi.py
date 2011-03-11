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


class WikiFormatError(Exception):
    pass


def wiki_doc_to_dict(doc):
    wiki_dict = {}
    last_key = None
    lines = doc.splitlines()
    for num, line in enumerate(lines):
        if line.find(':') < 0:
            if last_key is None:
                raise WikiFormatError('bad wiki formatting:\n%s' % '\n'.join(lines[:num]))
            line = line.strip()
            if line.startswith('*'):
                line = ' ' + line
            line += '\n'
            wiki_dict[last_key] += line
        else:
            key, remainder = line.split(':', 1)
            key = key.strip()
            remainder = remainder.strip()
            wiki_dict[key] = remainder + '\n'
            last_key = key
    return wiki_dict


def format_wiki_doc(doc):
    wiki_dict = wiki_doc_to_dict(doc)
    wiki_doc = '== %s ==\n' % wiki_dict.get('title', 'Untitled').strip()
    wiki_doc += "''%s''\n" % wiki_dict.get('description', 'No description\n').strip()
    wiki_doc += '[[BR]]\n[[BR]]\n'
    for key in ('method', 'path', 'permission', 'success response',
                'failure response', 'return', 'object fields', 'filters'):
        wiki_doc += "'''%s:''' %s" % (key, wiki_dict.get(key, 'Unspecified\n'))
        wiki_doc += '[[BR]]\n'
    return wiki_doc


def process_doc_string(doc):
    doc_string, wiki_doc = doc_marker.split(doc)
    wiki_doc = wiki_doc.strip()
    if not wiki_doc:
        return ''
    return format_wiki_doc(wiki_doc)


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
    docs = []
    cls = import_base_class()
    for name, attr in module.__dict__.items():
        if not (type(attr) == types.TypeType and issubclass(attr, cls)):
            continue
        docs.append(gen_docs_for_class(attr))
    return docs


def write_docs_for_module(dir, module_name, docs):
    title = module_name.split('.')[-1]
    file_name = '%s.wiki' % title
    file_path = os.path.join(os.path.abspath(dir), file_name)
    file = open(file_path, 'w')
    file.write('[[TOC]]\n= %s REST API =' % title.title())
    file.write('\n\n'.join(docs))
    file.close()

# -----------------------------------------------------------------------------

def main():
    opts = parse_args()
    sys.path.insert(0, opts.src)
    for module in import_modules():
        try:
            docs = gen_docs_for_module(module)
            write_docs_for_module(opts.out, module.__name__, docs)
        except Exception, e:
            print >> sys.stderr, 'doc generation for %s failed' % module.__name__
            print >> sys.stderr, ''.join(traceback.format_exception(*sys.exc_info()))
            print >> sys.stderr, str(e)
            continue
    return os.EX_OK


if __name__ == '__main__':
    sys.exit(main())
