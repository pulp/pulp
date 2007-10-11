# -*- coding: utf-8 -*-
# Kid template module
kid_version = '0.9.6'
kid_file = '/home/mmccune/devel/trunk/playpen/turbogears/pulp/pulp/templates/nav.kid'
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
		ancestors.insert(0, current)
		current = Element(u'div', {u'id': u'navbar'})
		for _p, _u in {u'py': u'http://purl.org/kid/ns#'}.items():
			if not _u in omit_namespaces: yield START_NS, (_p,_u)
		yield START, current
		yield TEXT, u'\n\t'
		ancestors.insert(0, current)
		current = Element(u'ul', {})
		yield START, current
		yield TEXT, u'\n\t  '
		for t in tabs:
			ancestors.insert(0, current)
			current = Element(u'span', {})
			yield START, current
			yield TEXT, u' \n\t  '
			if t.active:
				ancestors.insert(0, current)
				current = Element(u'li', {u'class': u'active'})
				yield START, current
				yield TEXT, u'\n\t    '
				ancestors.insert(0, current)
				current = Element(u'a', template_util.make_attrib({u'href': [t.url]}, self._get_assume_encoding()))
				yield START, current
				for _e in [t.name]:
					for _e2 in template_util.generate_content(_e): yield _e2
				yield END, current
				current = ancestors.pop(0)
				yield TEXT, u'\n\t  '
				yield END, current
				current = ancestors.pop(0)
			yield TEXT, u'\n      '
			if not t.active:
				ancestors.insert(0, current)
				current = Element(u'li', {})
				yield START, current
				yield TEXT, u'\n        '
				ancestors.insert(0, current)
				current = Element(u'a', template_util.make_attrib({u'href': [t.url]}, self._get_assume_encoding()))
				yield START, current
				for _e in [t.name]:
					for _e2 in template_util.generate_content(_e): yield _e2
				yield END, current
				current = ancestors.pop(0)
				yield TEXT, u'\n      '
				yield END, current
				current = ancestors.pop(0)
			yield TEXT, u'\n\t  '
			yield END, current
			current = ancestors.pop(0)
		yield TEXT, u'\n\t'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
