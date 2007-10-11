# -*- coding: utf-8 -*-
# Kid template module
kid_version = '0.9.6'
kid_file = '/home/mmccune/devel/trunk/playpen/turbogears/pulp/pulp/templates/search.kid'
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
		yield TEXT, u'LoginPage'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}body', {})
		yield START, current
		yield TEXT, u'\n'
		_cont = search_form.display(submit_text='Login')
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}p', {})
		yield START, current
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}br', {})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n\n\n'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}br', {})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
