# -*- coding: utf-8 -*-
# Kid template module
kid_version = '0.9.6'
kid_file = '/home/mmccune/devel/trunk/playpen/turbogears/pulp/pulp/templates/welcome.kid'
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
doctype = (u'html', u'-//W3C//DTD XHTML 1.0 Transitional//EN', u'http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd')
BaseTemplate1 = template_util.base_class_extends("'master.kid'", globals(), {}, "'master.kid'")
class Template(BaseTemplate1, BaseTemplate):
	_match_templates = []
	def initialize(self):
		rslt = initialize(self)
		if rslt != 0: super(Template, self).initialize()
	def _pull(self):
		exec template_util.get_locals(self, locals())
		current, ancestors = None, []
		if doctype: yield DOCTYPE, doctype
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}html', {})
		for _p, _u in {'': u'http://www.w3.org/1999/xhtml', u'py': u'http://purl.org/kid/ns#'}.items():
			if not _u in omit_namespaces: yield START_NS, (_p,_u)
		yield START, current
		yield TEXT, u'\n'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}head', {})
		yield START, current
		yield TEXT, u'\n'
		_cont = ''
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield TEXT, u'\n'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}title', {})
		yield START, current
		yield TEXT, u'Welcome to TurboGears'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}body', {})
		yield START, current
		yield TEXT, u'\n\n  '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}div', {u'id': u'getting_started'})
		yield START, current
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}ol', {u'id': u'getting_started_steps'})
		yield START, current
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}li', {u'class': u'getting_started'})
		yield START, current
		yield TEXT, u'\n        '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}h3', {})
		yield START, current
		yield TEXT, u'Model'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n        '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}p', {})
		yield START, current
		yield TEXT, u' '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}a', {u'href': u'http://docs.turbogears.org/1.0/GettingStarted/DefineDatabase'})
		yield START, current
		yield TEXT, u'Design models'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u' in the '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}span', {u'class': u'code'})
		yield START, current
		yield TEXT, u'model.py'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'.'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}br', {})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n          Edit '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}span', {u'class': u'code'})
		yield START, current
		yield TEXT, u'dev.cfg'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u' to '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}a', {u'href': u'http://docs.turbogears.org/1.0/GettingStarted/UseDatabase'})
		yield START, current
		yield TEXT, u'use a different backend'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u', or start with a pre-configured SQLite database. '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}br', {})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n          Use script '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}span', {u'class': u'code'})
		yield START, current
		yield TEXT, u'tg-admin sql create'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u' to create the database tables.'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}li', {u'class': u'getting_started'})
		yield START, current
		yield TEXT, u'\n        '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}h3', {})
		yield START, current
		yield TEXT, u'View'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n        '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}p', {})
		yield START, current
		yield TEXT, u' Edit '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}a', {u'href': u'http://docs.turbogears.org/1.0/GettingStarted/Kid'})
		yield START, current
		yield TEXT, u'html-like templates'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u' in the '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}span', {u'class': u'code'})
		yield START, current
		yield TEXT, u'/templates'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u' folder;'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}br', {})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n        Put all '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}a', {u'href': u'http://docs.turbogears.org/1.0/StaticFiles'})
		yield START, current
		yield TEXT, u'static contents'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u' in the '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}span', {u'class': u'code'})
		yield START, current
		yield TEXT, u'/static'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u' folder. '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}li', {u'class': u'getting_started'})
		yield START, current
		yield TEXT, u'\n        '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}h3', {})
		yield START, current
		yield TEXT, u'Controller'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n        '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}p', {})
		yield START, current
		yield TEXT, u' Edit '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}span', {u'class': u'code'})
		yield START, current
		yield TEXT, u' controllers.py'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u' and '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}a', {u'href': u'http://docs.turbogears.org/1.0/GettingStarted/CherryPy'})
		yield START, current
		yield TEXT, u'build your\n          website structure'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u' with the simplicity of Python objects. '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}br', {})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n          TurboGears will automatically reload itself when you modify your project. '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}div', {u'class': u'notice'})
		yield START, current
		yield TEXT, u' If you create something cool, please '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}a', {u'href': u'http://groups.google.com/group/turbogears'})
		yield START, current
		yield TEXT, u'let people know'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u', and consider contributing something back to the '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}a', {u'href': u'http://groups.google.com/group/turbogears'})
		yield START, current
		yield TEXT, u'community'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'.'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n  '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n  '
		_e = Comment(u' End of getting_started ')
		yield START, _e; yield END, _e; del _e
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
