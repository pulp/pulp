#!/usr/bin/env python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>
#

"""
Tool to expand decorators into python 2.3 compat syntax.
"""

import os
import sys
from optparse import OptionParser
from StringIO import StringIO


class Line(object):

    def __init__(self, ln, num=0):
        self.indent, self.ln = self.split(ln)
        self.num = num
        self.decorators = []

    def append(self, ln):
        self.body.append(ln)

    def iscomment(self):
        return self.ln.startswith('#')

    def isdecorator(self):
        return self.ln.startswith('@')

    def isfunction(self):
        return self.ln.startswith('def')

    def ismlquote(self):
        s = self.ln.strip()
        n = s.count('"""')
        if n == 1: # only 1 found
            return True
        n = s.count("'''")
        if n == 1: # only 1 found
            return True
        return False

    def isblank(self):
        return self.ln.strip() == ''

    def split(cls, ln):
        n = 0
        for c in ln:
            if c != ' ': break
            n += 1
        return (n, ln[n:].strip())

    def __str__(self):
        return str((self.indent, self.ln, str(self.decorators)))

    def __eq__(self, other):
        return self.indent == other.indent

    def __gt__(self, other):
        return self.indent > other.indent

    def __lt__(self, other):
        return self.indent < other.indent
    
    def __cmp__(self, other):
        if self.indent < other.indent:
            return -1
        if self.indent > other.indent:
            return 1
        return 0


class Decorator:

    def __init__(self, fn, decorator):
        self.fn = str(fn)
        self.decorator = decorator

    def __str__(self):
        fn = self.fn
        decorator = self.decorator.ln[1:]
        if '(' in decorator:
            name, argpart = decorator.split('(', 1)
            arglist = argpart[:-1]
            return '%s(%s)(%s)' % (name, arglist, fn)
        else:
            return '%s(%s)' % (decorator, fn)


class Indent:
    def __init__(self, n):
        self.n = n

    def __str__(self):
        if self.n:
            return '%*s' % (self.n,' ')
        else:
            return ''


class MockDecorator:
    def __init__(self, fn):
        self.fn = fn

    def __str__(self):
        fn = self.fn
        n =  Indent(fn.indent)
        decl = fn.ln.split(' ', 1)[1]
        name, args = decl.split('(', 1)
        dx = name
        for d in fn.decorators:
            dx = Decorator(dx, d)
        return '\n%s%s = %s' % (n, name, dx)


class Patch:

    def __init__(self, popped, md):
        self.popped = popped
        self.md = md

    def fmt(self, ln, sign=''):
        return '%4s: %s%s' % (ln.num, sign, ln.ln)

    def indent(self, n): return '%*s'%(n,' ')

    def __str__(self):
        s = []
        indent = self.indent(6)
        for d in self.popped.decorators:
            chg = self.fmt(d, '- ')
            s.append(chg)
        s.append(self.fmt(self.popped))
        s.append('%s...' % indent)
        md = str(self.md).strip()
        chg = '%s+ %s' % (indent, md)
        s.append(chg)
        return '\n'.join(s)


class Parser:

    def __init__(self):
        self.stack = []

    def top(self):
        if self.stack:
            return self.stack[-1]
        else:
            return Line('')

    def push(self, ln):
        self.stack.append(ln)

    def pop(self):
        if self.stack:
            return self.stack.pop()
        else:
            return Line('')

    def decorator(self, ln):
        self.push(ln)

    def function(self, ln):
        decorators = []
        while self.top().isdecorator():
            decorators.append(self.pop())
            if decorators:
                ln.decorators = decorators
                self.push(ln)

    def end(self, out):
        if self.top().isfunction():
            popped = self.pop()
            md = MockDecorator(popped)
            return Patch(popped, md)

    def parse(self, fp, ofp=sys.stdout):
        lnum = 0
        chgset = []
        docstring = 0
        self.stack = []
        while True:
            lnum += 1
            s = fp.readline()
            if not s:
                break
            ln = Line(s, lnum)
            if ln.isblank():
                ofp.write(s)
                continue
            if ln.iscomment():
                ofp.write(s)
                continue
            if ln.ismlquote():
                docstring = (not docstring)
                ofp.write(s)
                continue
            if docstring:
                ofp.write(s)
                continue
            if ln <= self.top():
                chg = self.end(ofp)
                if chg:
                    ofp.write(str(chg.md))
                    ofp.write('\n\n')
                    chgset.append(chg)
            if ln.isdecorator():
                self.decorator(ln)
                continue
            if ln.isfunction():
                self.function(ln)
                ofp.write(s)
                continue
            # other
            ofp.write(s)
        if self.stack:
            chg = self.end(ofp)
            if chg:
                ofp.write(str(chg.md))
                ofp.write('\n')
                chgset.append(chg)
        return chgset


class Directory:

    def __init__(self, path):
        assert not os.path.isfile(path)
        self.path = os.path.normpath(path)

    def create(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def list(self, filter=2, depth=0):
        list = []
        path = self.path
        for p in os.listdir(path):
            p = os.path.join(path, p)
            if os.path.isdir(p):
                if filter in (0,2):
                    list.append(p+'/')
                if depth > 0:
                    d = Directory(p)
                    list += d.list(filter, depth-1)
            else:
                if filter in (1,2):
                    list.append(p)
        return list

    def tree(self, filter=2, depth=sys.maxint):
        return self.list(filter, depth)

    def mirror(self, path):
        path = str(path)
        if path == self.path:
            return
        self.create()
        other = Directory(path)
        for p in other.tree(filter=0):
            p = p.replace(path, self.path)
            if os.path.exists(p):
                continue
            print '(mirror) making: %s' % p
            os.makedirs(p)


    def __str__(self):
        return str(self.path)

    def __eq__(self, other):
        if isinstance(other, Directory):
            return other.path == self.path
        else:
            return other == self.path


def summary(chgset, fp=sys.stdout):
    fp.write('summary:\n')
    for patch in chgset:
        fp.write(str(patch))
        fp.write('\n\n')
        fp.flush()


def piped():
    p = Parser()
    chgset = p.parse(sys.stdin)
    log = __log()
    summary(chgset, log)
    close(log)


def inline(path):
    p = Parser()
    log = sys.stdout
    indir = Directory(path)
    for fn in indir.tree(filter=1):
        if not fn.endswith('.py'):
            continue
        log.write('\nfile: %s\n' % fn)
        fp = open(fn)
        content = fp.read()
        close(fp)
        fp = StringIO(content)
        ofp = open(fn, 'w')
        chgset = p.parse(fp, ofp)
        summary(chgset, log)
        close(ofp)
    close(log)


def process(path, outdir=None):
    p = Parser()
    if outdir:
        log = sys.stdout
    else:
        log = __log()
    if os.path.isdir(path):
        indir = Directory(path)
        files = indir.tree(filter=1)
    else:
        indir = Directory(os.path.dirname(path))
        files = (path,)
    if outdir:
        outdir = Directory(outdir)
        outdir.create()
        if os.path.isdir(path):
            outdir.mirror(indir)
    for fn in files:
        if not fn.endswith('.py'):
            continue
        log.write('\nfile: %s\n' % fn)
        fp = open(fn)
        if outdir:
            ofn = fn.replace(indir.path, outdir.path)
            ofp = open(ofn, 'w')
        else:
            ofp = sys.stdout
        chgset = p.parse(fp, ofp)
        summary(chgset, log)
        close(fp, ofp)
    close(log)


def close(*fps):
    for fp in fps:
        if fp in (sys.stdin, sys.stdout, sys.stderr):
            continue
        fp.close()


def __log():
    path = sys.argv[0].split('.')[0]
    prog = os.path.basename(path)
    logpath = '/tmp/%s.log' % prog
    return open(logpath, 'w')


def __parser():
    parser = OptionParser()
    parser.add_option(
        '-o',
        '--outdir',
        dest='outdir',
        help='output directory')
    parser.add_option(
        '-I', '--inline',
        dest='inline',
        default=False,
        action='store_true',
        help='Perform inline substitution of imput files')
    return parser


def main():
    parser = __parser()
    (opt, args) = parser.parse_args()
    if args:
        if opt.inline:
            inline(args[0])
        else:
            process(args[0], opt.outdir)
    else:
        piped()


if __name__ == '__main__':
    main()
