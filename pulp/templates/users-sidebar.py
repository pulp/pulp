# -*- coding: utf-8 -*-
# Kid template module
kid_version = '0.9.6'
kid_file = '/home/mmccune/devel/trunk/playpen/turbogears/pulp/pulp/templates/users-sidebar.kid'
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
		yield TEXT, u'Update my password'
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
		yield TEXT, u'Update my contact information'
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
		yield TEXT, u'About Users:'
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
		yield TEXT, u'Add a new user'
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
		yield TEXT, u'Other users on my team'
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
		yield TEXT, u'Other users in my department'
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
		yield TEXT, u'Other users in my office'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    \n    '
		ancestors.insert(0, current)
		current = Element(u'hr', {})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    \n    '
		ancestors.insert(0, current)
		current = Element(u'h3', {})
		yield START, current
		yield TEXT, u'Find a User:'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'input', {u'type': u'text', u'class': u'text', u'value': u'Type search terms here.'})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'input', {u'type': u'submit', u'class': u'button', u'value': u'Search!'})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    \n    '
		ancestors.insert(0, current)
		current = Element(u'hr', {})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    \n      '
		ancestors.insert(0, current)
		current = Element(u'ul', {u'id': u'navbar-secondary'})
		yield START, current
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'li', {u'class': u'active'})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'a', {u'href': u'#'})
		yield START, current
		yield TEXT, u'Browse Users'
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
		yield TEXT, u'Browse User Groups'
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
		yield TEXT, u'Search for Users'
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
		yield TEXT, u'Manage User Policies'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
		_e = Comment(u' END SIDEBAR ')
		yield START, _e; yield END, _e; del _e
