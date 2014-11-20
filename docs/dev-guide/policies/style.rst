Style
=====

PEP-8
-----

New Pulp code should adhere as closely as is reasonable to PEP-8. One modification is that our line
length limit is 100 characters, which we chose to prevent line wrapping on GitHub.


In-code Documentation
---------------------

Document your functions using the markup described
`here <http://sphinx-doc.org/markup/desc.html#info-field-lists>`_.
If it's worth having a function, it's worth taking 1 minute to describe what it
does, define each parameter, and define its return value. This saves a
tremendous amount of time for the next person who looks at your code.

Include reasonable in-line comments where they might be helpful.


Naming
------

Use meaningful names.

Bad::

  def update(t, n, p):

Good::

  def update(title, name, path):

Be mindful of the global namespace, and don't collide with builtins and standard
library components. For example, don't name anything "id", "file", "copy" etc.


Indentation
-----------

4 spaces, never tabs


Encoding
--------

Specify UTF-8 encoding in each file:

::

  # -*- coding: utf-8 -*-
