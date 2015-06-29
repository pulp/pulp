Style
=====

PEP-8
-----

New Pulp code should adhere as closely as is reasonable to PEP-8. One modification is that our line
length limit is 100 characters, which we chose to prevent line wrapping on GitHub.


In-code Documentation
---------------------

All new code must have a doc block that describes what the function or class does,
describes each of the parameters and its type (fully qualified please), lists
exceptions that can be raised, and describes the return value and its type.

Example::

  def update(title, author, book):
      """
      Updates information about a book and returns the updated object.

      :param title: new title the book should be assigned
      :type  title: basestring
      :param author: new author that the book should be assigned
      :type  author: fully.qualified.author
      :param book: book object that will be updated
      :type  book: fully.qualified.book

      :raises BookNotFound: if book is not found

      :return: updated book object
      :rtype:  fully.qualified.book
      """
      if book is None:
          raise BookNotFound
      _do_update(title, author, book)
      return book


More details on the markup is described
`here <http://sphinx-doc.org/domains.html#info-field-lists>`_.

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
