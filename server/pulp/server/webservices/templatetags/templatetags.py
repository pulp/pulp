"""Vebratim template tag for Django 1.4.

Designed for Django 1.4
For newer versions to at least 1.9 the code is same and nothing happens if included.
For older versions I have not tested it.

All code below is inspired by Django 1.5

https://github.com/django/django/blob/stable/1.5.x/django/template/base.py
https://github.com/django/django/blob/stable/1.5.x/django/template/defaulttags.py

This module should be removed from pulp as soon as pulp drops el6 support.
"""
from django.template import base
from django.template.base import (BLOCK_TAG_START, COMMENT_TAG_START,
                                  TOKEN_BLOCK, TOKEN_COMMENT, TOKEN_TEXT,
                                  TOKEN_VAR, TRANSLATOR_COMMENT_MARK,
                                  VARIABLE_TAG_START, Context, Lexer, Node,
                                  Token)
from django.template.defaulttags import register


class VerbatimNode(Node):
    def __init__(self, content):
        self.content = content

    def render(self, context):
        return self.content


class _Lexer(Lexer):
    verbatim = False

    def create_token(self, token_string, in_tag):
        """
        Convert the given token string into a new Token object and return it.
        If in_tag is True, we are processing something that matched a tag,
        otherwise it should be treated as a literal string.
        """
        if in_tag and token_string.startswith(BLOCK_TAG_START):
            # The [2:-2] ranges below strip off *_TAG_START and *_TAG_END.
            # We could do len(BLOCK_TAG_START) to be more "correct", but we've
            # hard-coded the 2s here for performance. And it's not like
            # the TAG_START values are going to change anytime, anyway.
            block_content = token_string[2:-2].strip()
            if self.verbatim and block_content == self.verbatim:
                self.verbatim = False
        if in_tag and not self.verbatim:
            if token_string.startswith(VARIABLE_TAG_START):
                token = Token(TOKEN_VAR, token_string[2:-2].strip())
            elif token_string.startswith(BLOCK_TAG_START):
                if block_content[:9] in ('verbatim', 'verbatim '):
                    self.verbatim = 'end%s' % block_content
                token = Token(TOKEN_BLOCK, block_content)
            elif token_string.startswith(COMMENT_TAG_START):
                content = ''
                if token_string.find(TRANSLATOR_COMMENT_MARK):
                    content = token_string[2:-2].strip()
                token = Token(TOKEN_COMMENT, content)
        else:
            token = Token(TOKEN_TEXT, token_string)
        token.lineno = self.lineno
        self.lineno += token_string.count('\n')
        return token


@register.tag
def verbatim(parser, token):
    """
    Stops the template engine from rendering the contents of this block tag.
    Usage::
        {% verbatim %}
            {% don't process this %}
        {% endverbatim %}
    You can also designate a specific closing tag block (allowing the
    unrendered use of ``{% endverbatim %}``)::
        {% verbatim myblock %}
            ...
        {% endverbatim myblock %}
    """
    nodelist = parser.parse(('endverbatim',))
    parser.delete_first_token()
    return VerbatimNode(nodelist.render(Context()))


base.Lexer = _Lexer
