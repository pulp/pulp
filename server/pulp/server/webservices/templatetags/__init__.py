"""Pulp backport of verbatim tag from Django 1.5.

For more info take a look at pulp.server.webservices.templatetags.templatetags.

This Package loads verbatim tag only if version is smaller than 1.5  and have version 1
eg. 1.0 -> 1.4 - verbatim tag is designed for Django 1.4.
On Django 1.3 - The tag does not support named verbatim blocks and therefore escaping
{% verbatim %} tags inside.
"""
import django

if django.VERSION[0] == 1 and django.VERSION[1] < 5:
    import templatetags  # NOQA
