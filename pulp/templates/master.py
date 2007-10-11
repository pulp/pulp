# -*- coding: utf-8 -*-
# Kid template module
kid_version = '0.9.6'
kid_file = '/home/mmccune/devel/trunk/playpen/turbogears/pulp/pulp/templates/master.kid'
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
import sitetemplate
BaseTemplate1 = template_util.base_class_extends('sitetemplate', globals(), {}, 'sitetemplate')
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
		yield TEXT, u'\n\n'
		yield TEXT, u'\n'
		yield TEXT, u'\n\n'
		yield END, current
		current = ancestors.pop(0)
	def _match_func(self, item, apply):
		exec template_util.get_locals(self, locals())
		current, ancestors = None, []
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}head', template_util.make_updated_attrib({}, "item.items()", globals(), locals(), self._get_assume_encoding()))
		yield START, current
		yield TEXT, u'\n    '
		_cont = ''
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield TEXT, u'\n    '
		_cont = ''
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield TEXT, u'\n    '
		_cont = item[:]
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}style', {u'type': u'text/css'})
		yield START, current
		yield TEXT, u'\n        #pageLogin\n        {\n            font-size: 10px;\n            font-family: verdana;\n            text-align: right;\n        }\n    '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}style', {u'media': u'screen', u'type': u'text/css'})
		yield START, current
		for _e in [u'\n@import "', tg.url('/static/css/style.css'), u'";\n']:
			for _e2 in template_util.generate_content(_e): yield _e2
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
	_match_templates.append((lambda item: item.tag=='{http://www.w3.org/1999/xhtml}head', _match_func))
	def _match_func(self, item, apply):
		exec template_util.get_locals(self, locals())
		current, ancestors = None, []
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}body', template_util.make_updated_attrib({}, "item.items()", globals(), locals(), self._get_assume_encoding()))
		yield START, current
		yield TEXT, u'\n    '
		if tg.config('identity.on') and not defined('logging_in'):
			ancestors.insert(0, current)
			current = Element(u'{http://www.w3.org/1999/xhtml}div', {u'id': u'pageLogin'})
			yield START, current
			yield TEXT, u'\n        '
			if tg.identity.anonymous:
				ancestors.insert(0, current)
				current = Element(u'{http://www.w3.org/1999/xhtml}span', {})
				yield START, current
				yield TEXT, u'\n            '
				ancestors.insert(0, current)
				current = Element(u'{http://www.w3.org/1999/xhtml}a', template_util.make_attrib({u'href': [tg.url('/login')]}, self._get_assume_encoding()))
				yield START, current
				yield TEXT, u'Login'
				yield END, current
				current = ancestors.pop(0)
				yield TEXT, u'\n        '
				yield END, current
				current = ancestors.pop(0)
			yield TEXT, u'\n        '
			if not tg.identity.anonymous:
				ancestors.insert(0, current)
				current = Element(u'{http://www.w3.org/1999/xhtml}span', {})
				yield START, current
				for _e in [u'\n            Welcome ', tg.identity.user.display_name, u'.\n            ']:
					for _e2 in template_util.generate_content(_e): yield _e2
				ancestors.insert(0, current)
				current = Element(u'{http://www.w3.org/1999/xhtml}a', template_util.make_attrib({u'href': [tg.url('/logout')]}, self._get_assume_encoding()))
				yield START, current
				yield TEXT, u'Logout'
				yield END, current
				current = ancestors.pop(0)
				yield TEXT, u'\n        '
				yield END, current
				current = ancestors.pop(0)
			yield TEXT, u'\n    '
			yield END, current
			current = ancestors.pop(0)
		yield TEXT, u'\n    \n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}div', {u'id': u'head'})
		yield START, current
		yield TEXT, u'\n'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}h1', {})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}a', {u'href': u'/'})
		yield START, current
		yield TEXT, u'Buster'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n\n'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}div', {u'id': u'searchbar'})
		yield START, current
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}select', {})
		yield START, current
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}option', {})
		yield START, current
		yield TEXT, u'Systems'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}option', {})
		yield START, current
		yield TEXT, u'Software'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}option', {})
		yield START, current
		yield TEXT, u'Users'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n      '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}option', {})
		yield START, current
		yield TEXT, u'Events'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}input', {u'type': u'text', u'class': u'text', u'value': u'Type search terms here.'})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}input', {u'type': u'submit', u'class': u'button', u'value': u'Search!'})
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n  '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n\n'
		_e = Comment(u'  Nav Bar ')
		yield START, _e; yield END, _e; del _e
		yield TEXT, u'\n'
		_cont = tg.buildnav('pulp/master.xml')
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield TEXT, u'\n\n'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}div', {u'id': u'content'})
		yield START, current
		yield TEXT, u'\n\n'
		_e = Comment(u' SIDEBAR START ')
		yield START, _e; yield END, _e; del _e
		yield TEXT, u'\n'
		_cont = tg.if_path('/', 'pulp.templates.overview-sidebar')
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield TEXT, u'\n'
		_cont = tg.if_path('/users', 'pulp.templates.users-sidebar')
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield TEXT, u'\n'
		_cont = tg.if_path('/groups', 'pulp.templates.groups-sidebar')
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield TEXT, u'\n'
		_cont = tg.if_path('/search', 'pulp.templates.groups-sidebar')
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield TEXT, u'\n'
		_e = Comment(u' END SIDEBAR ')
		yield START, _e; yield END, _e; del _e
		yield TEXT, u'\n\n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}FONT', {u'COLOR': u'gray'})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}h1', {})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}span', {})
		yield START, current
		yield TEXT, u'START MAIN CONTENT'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    \n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}div', {u'id': u'main_content'})
		yield START, current
		yield TEXT, u'\n    '
		if value_of('tg_flash', None):
			_cont = tg_flash
			ancestors.insert(0, current)
			current = Element(u'{http://www.w3.org/1999/xhtml}div', {u'id': u'status_block', u'class': u'flash'})
			yield START, current
			for _e in template_util.generate_content(_cont):
				yield _e
				del _e
			yield END, current
			current = ancestors.pop(0)
		yield TEXT, u'\n\n    '
		_cont = [item.text]+item[:]
		for _e in template_util.generate_content(_cont):
			yield _e
			del _e
		yield TEXT, u'\n    '
		_e = Comment(u' End of main_content ')
		yield START, _e; yield END, _e; del _e
		yield TEXT, u'\n    '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}FONT', {u'COLOR': u'gray'})
		yield START, current
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}h1', {})
		yield START, current
		yield TEXT, u'END MAIN CONTENT'
		yield END, current
		current = ancestors.pop(0)
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    '
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n\n'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n    \n    \n'
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}div', {u'id': u'footer'})
		yield START, current
		yield TEXT, u' '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}img', template_util.make_attrib({u'src': [tg.url('/static/images/under_the_hood_blue.png')], u'alt': u'TurboGears under the hood'}, self._get_assume_encoding()))
		yield START, current
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n  '
		ancestors.insert(0, current)
		current = Element(u'{http://www.w3.org/1999/xhtml}p', {})
		yield START, current
		yield TEXT, u'TurboGears is a open source front-to-back web development\n    framework written in Python'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
		yield TEXT, u'\n'
		yield END, current
		current = ancestors.pop(0)
	_match_templates.append((lambda item: item.tag=='{http://www.w3.org/1999/xhtml}body', _match_func))
