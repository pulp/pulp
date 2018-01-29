Dependencies
============

The Pulp Platform is built using two key frameworks, the Django Web Framework
and the Django REST Framework. Where possible, conforming to the conventions
of these frameworks is encouraged. The Pulp Platform strives to leverage these
frameworks as much as possible, ideally making Pulp Platform development a
work of implementation before innovation.

In the event that one of these components offers functionality that augments
or supersedes functionality in another component, the order of precedence of
these frameworks is:

* Pulp Platform
* Django REST Framework (DRF)
* Django Web Framework (Django)

So, features provided by the Pulp Platform should preferred over similar
features provided by DRF, and features in DRF should be preferred over similar
features provided by Django.
