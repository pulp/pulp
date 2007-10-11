# -*- coding: utf-8 -*-
# Kid template module
kid_version = '0.9.6'
kid_file = '/home/mmccune/devel/trunk/playpen/turbogears/pulp/pulp/templates/overview-sidebar.kid'
import kid
from kid.template_util import *
import kid.template_util as template_util
_def_names = []
encoding = "utf-8"
doctype = None
omit_namespaces = [kid.KID_XMLNS]
layout_params = {}
def pull(**kw): return Template(**kw).pull()
def generate(encoding=encoding, fragment=False, output=None, format=None, **kw): return Template(**kw).generate(encoding=encoding, fragment=fragment, output=output, format=format)
def serialize(encoding=encoding, fragment=False, output=None, format=None, **kw): return Template(**kw).serialize(encoding=encoding, fragment=fragment, output=output, format=format)
def write(file, encoding=encoding, fragment=False, output=None, format=None, **kw): return Template(**kw).write(file, encoding=encoding, fragment=fragment, output=output, format=format)
def initialize(template): pass
BaseTemplate = kid.BaseTemplate
class Template(BaseTemplate):
	_match_templates = []
	def initialize(self):
		rslt = initialize(self)
		if rslt != 0: super(Template, self).initialize()
	def _pull(self):
		exec template_util.get_locals(self, locals())
		current, ancestors = None, []
		if doctype: yield DOCTYPE, doctype
		_e = Comment(u' SIDEBAR START ')
		yield START, _e; yield END, _e; del _e
		ancestors.insert(0, current)
		current = Element(u'div', {u'id': u'sidebar'})
		yield START, current
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'h2', {})
		yield START, current
		yield TEXT, u'About My Overview:'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'ul', {})
		yield START, current
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'li', {})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'a', {u'href': u'#'})
		yield START, current
		yield TEXT, u'Add a new perspective'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'li', {})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'a', {u'href': u'#'})
		yield START, current
		yield TEXT, u'Customize my info feed'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'li', {})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'a', {u'href': u'#'})
		yield START, current
		yield TEXT, u'Modify my overview page layout'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    \n    '
		ancestors.insert(0, current)
		current = Element(u'h2', {})
		yield START, current
		yield TEXT, u'About Me:'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'ul', {})
		yield START, current
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'li', {})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'a', {u'href': u'#'})
		yield START, current
		yield TEXT, u'Update my password / contact info'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'hr', {})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    \n    '
		ancestors.insert(0, current)
		current = Element(u'h3', {})
		yield START, current
		yield TEXT, u'My Roles:'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'ul', {})
		yield START, current
		yield TEXT, u'\n        '
		ancestors.insert(0, current)
		current = Element(u'li', {})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'strong', {})
		yield START, current
		yield TEXT, u'Content Owner '
		ancestors.insert(0, current)
		current = Element(u'a', {u'href': u'#'})
		yield START, current
		yield TEXT, u'(more ...)'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n        '
		ancestors.insert(0, current)
		current = Element(u'li', {})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'strong', {})
		yield START, current
		yield TEXT, u'System Owner '
		ancestors.insert(0, current)
		current = Element(u'a', {u'href': u'#'})
		yield START, current
		yield TEXT, u'(more ...)'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'hr', {})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
		_e = Comment(u' END SIDEBAR ')
		yield START, _e; yield END, _e; del _e
