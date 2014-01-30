Style
=====

PEP-8
-----

New Pulp code should adhere as closely as is reasonable to PEP-8. One
exception is the line length limit, which we are more flexible about. In order to prevent
line wrapping when code is viewed on github it is recommended that line length be limited
to 100 characters but do whatever makes sense.


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


Copyright
---------

Use the UTF-8 copyright character and GPL 2, so each code file begins as such:

::

  # -*- coding: utf-8 -*-
  #
  # Copyright © 2013 Red Hat, Inc.
  #
  # This software is licensed to you under the GNU General Public
  # License as published by the Free Software Foundation; either version
  # 2 of the License (GPLv2) or (at your option) any later version.
  # There is NO WARRANTY for this software, express or implied,
  # including the implied warranties of MERCHANTABILITY,
  # NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
  # have received a copy of GPLv2 along with this software; if not, see
  # http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
