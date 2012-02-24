#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import inspect
import itertools
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
    opts, args = parser.parse_args(args)
    return opts

# -----------------------------------------------------------------------------

_parent_module = 'pulp.server.webservices.controllers'

_module_names = ('audit', 'cds', 'consumergroups', 'consumers',
                 'distribution', 'filters', 'orphaned', 'packages',
                 'permissions', 'repositories', 'roles', 'services', 'tasks',
                 'users', 'jobs',)


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

required_keys = ('title', 'description')
default_keys = ('method', 'path', 'permission', 'success response', 'failure response', 'return')
optional_keys = ('example', 'parameters', 'filters')


class WikiDict(dict):
    """
    "Ordered" dictionary class.
    """
    def __init__(self, *args, **kwargs):
        super(WikiDict, self).__init__(*args, **kwargs)
        self._keys = []

    def __setitem__(self, key, value):
        super(WikiDict, self).__setitem__(key, value)
        if key not in self._keys:
            self._keys.append(key)

    def keys(self):
        return self._keys[:]

    def values(self):
        return (self[k] for k in self.keys() if k in self)

    def items(self):
        return ((k, self[k]) for k in self.keys() if k in self)


class WikiFormatError(Exception):
    pass

# -----------------------------------------------------------------------------

def bold(s):
    return "'''%s'''" % s


def italic(s):
    return "''%s''" % s


def underline(s):
    return '__%s__' % s

# -----------------------------------------------------------------------------

def format_title(title):
    return ' '.join(t for t in title if t)


def format_description(description):
    return ' [[BR]]\n'.join(italic(l) for l in description) + ' [[BR]]\n'


def format_lines(lines):
    if len(lines) == 1:
        return lines[0] + ' [[BR]]\n'
    return '\n' + ' [[BR]]\n'.join(' ' + l for l in lines) + ' [[BR]]\n'


def format_list_entry(entry):
    entry = entry.strip()[2:]
    try:
        # try to split it out in to name, type, description
        n, t, d = entry.split(',', 2)
        n = n.strip()
        t = t.strip()
        d = d.strip()
        if n.endswith('?'):
            n = bold(n[:-1])
            n += " %s" % italic('(optional)')
        elif n.endswith('!'):
            n = bold(n[:-1])
            n += ' %s' % italic('(required)')
        else:
            n = bold(n)
        entry = "%s <%s> %s" % (n, t, italic(d))
    except ValueError:
        print >> sys.stderr, 'WARN: cannot list format: %s' % entry
    entry = ' * ' + entry
    return entry


def format_bulleted_list(blist):
    return '\n' + '\n'.join(format_list_entry(e) for e in blist) + '\n'


def format_preformatted(preformatted):
    index = preformatted[0].find('{{{')
    return '\n' + '\n'.join(l[index:] for l in preformatted) + '\n'


def format_value(key, value):
    if not value:
        return ''
    if key == 'title':
        return format_title(value)
    if key == 'description':
        return format_description(value)
    if value[-1].strip().startswith('*'):
        return format_bulleted_list(value)
    if value[0].strip().startswith('{{{'):
        return format_preformatted(value)
    return format_lines(value)

# -----------------------------------------------------------------------------

def _is_key_line(line):
    if line.endswith(':'):
        return True
    for key in itertools.chain(required_keys, default_keys, optional_keys):
        key_sentinal = key + ':'
        if key_sentinal in line:
            return True
    return False


def wiki_doc_to_dict(doc):
    """
    **THIS IS THE MAIN PARSER**
    Go through the wiki portion of the docstring and split out the key: value
    portions, and put them into an ordered dictionary.
    This function also does the majority of the formating.
    """
    wiki_dict = WikiDict()
    last_key = None
    last_value = []
    lines = doc.splitlines()
    for line in lines:
        if _is_key_line(line):
            if last_key is not None:
                wiki_dict[last_key] = format_value(last_key, last_value)
            key, remainder = line.split(':', 1)
            last_key = key.strip()
            last_value = []
            remainder = remainder.strip()
            if remainder:
                last_value.append(remainder)
        else:
            if last_key is None:
                raise WikiFormatError('bad wiki formatting:\n%s' % line)
            if line:
                last_value.append(line)
        if last_key is not None:
            wiki_dict[last_key] = format_value(last_key, last_value)
    return wiki_dict

# -----------------------------------------------------------------------------

def format_method_wiki_doc(doc):
    """
    Format the wiki portion of a method (read: controller) docstring.
    """
    wiki_dict = wiki_doc_to_dict(doc)
    # XXX need to figure out if there's a implicit way to reference the current page
    #wiki_doc = '[wiki:.#top back to top]\n'
    wiki_doc = '== %s ==\n' % wiki_dict.get('title', 'Untitled').strip()
    wiki_doc += wiki_dict.get('description', "%s [[BR]]\n" % italic('No description.'))
    wiki_doc += '[[BR]]\n'
    for key in itertools.chain(default_keys, optional_keys):
        if key in optional_keys and key not in wiki_dict:
            continue
        value = wiki_dict.get(key, 'Unspecified [[BR]]\n')
        wiki_doc += "%s: %s" % (bold(key), value)
        wiki_doc += '[[BR]]\n'
    return wiki_doc



def format_module_wiki_doc(module_name, doc):
    """
    Format the wiki portion of a module docstring.
    """
    def module_title():
        title = module_name.rsplit('.', 1)[1]
        return '%s RESTful API' % title.title()

    if doc is None:
        doc = ''
    wiki_dict = wiki_doc_to_dict(doc)
    wiki_doc = '= %s = #top\n' % wiki_dict.pop('title', module_title()).strip()
    wiki_doc += wiki_dict.pop('description', "%s [[BR]]\n" % italic('No description.'))
    wiki_doc += '[[BR]]\n'
    for key, value in wiki_dict.items():
        wiki_doc += "%s: %s" % (bold(key), value)
    return wiki_doc

# -----------------------------------------------------------------------------

def get_wiki_doc_string(obj):
    """
    Grok through an object's doc string, looking for the [[wiki]] sentinel.
    Return everything after the sentinel if it's found, return None otherwise.
    """
    name = getattr(obj, '__name__', 'Unnamed')
    doc = getattr(obj, '__doc__', None)
    if doc is None:
        print >> sys.stderr, 'skipped %s: no doc string' % name
        return None
    if not doc_marker.search(doc):
        print >> sys.stderr, 'skipped %s: no wiki formatting' % name
        return None
    doc_string, wiki_doc = doc_marker.split(doc)
    return wiki_doc.strip()


def gen_docs_for_class(cls):
    """
    Generate wiki docs from all of the docstrings found in a class.
    """
    docs = []
    # XXX this sorting isn't ideal
    for name, attr in sorted(cls.__dict__.items()):
        if not inspect.isroutine(attr):
            continue
        wiki_doc = get_wiki_doc_string(attr)
        if wiki_doc is not None:
            docs.append(format_method_wiki_doc(wiki_doc))
    return docs


def gen_docs_for_module(module):
    """
    Generate wiki docs for all of the docstrings found in a module.
    """
    docs = []
    wiki_doc = get_wiki_doc_string(module)
    docs.append(format_module_wiki_doc(module.__name__, wiki_doc))
    cls = import_base_class()
    # XXX this sorting isn't ideal
    for name, attr in sorted(module.__dict__.items()):
        if not (type(attr) == types.TypeType and issubclass(attr, cls)):
            continue
        cls_docs = gen_docs_for_class(attr)
        if not cls_docs:
            continue
        docs.append('----\n')
        docs.extend(cls_docs)
    return docs

# -----------------------------------------------------------------------------

_wiki_header = '''[[PageOutline]]
{{{
#!comment
!!!DO NOT EDIT DIRECTLY!!!
This wiki page was generated by the %s script
If you do edit this page directly, please remove this comment
}}}
''' % os.path.basename(__file__)


def write_docs_for_module(dir, module_name, docs):
    """
    Write out the wiki docs for a module to a text file.
    """
    title = module_name.split('.')[-1]
    file_name = '%s.wiki' % title
    file_path = os.path.join(os.path.abspath(dir), file_name)
    file = open(file_path, 'w')
    file.write(_wiki_header)
    file.write('\n'.join(docs))
    file.close()

# -----------------------------------------------------------------------------

def main():
    opts = parse_args()
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
