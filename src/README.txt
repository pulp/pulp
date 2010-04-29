Pulp Libraries and Applications

Pulp is a content management application that is made up of a core library and
collected applications running on top of it.

For more information on the architecture, please see:
https://fedorahosted.org/pulp/wiki/Architecture


Pulp --------------------------------------------------------------------------

The main library, this code base provides the main metaphors to wrap third-party
libraries and applications for the main source of functionality.

Detailed information can be found here:
https://fedorahosted.org/pulp/wiki/Library

Dependencies (required):


Dependencies (optional):


Juicer -----------------------------------------------------------------------

The web services layer, the code exposes a management API over a HTTP using a
RESTful interface and JSON encoding. It is a standalone daemon and does not
require Apache or another web server in order to run.

Detailed information can be found here:
https://fedorahosted.org/pulp/wiki/WebService

Dependencies (required):
 * Python  2.5   <http://www.python.org/>
 * Tornado 0.2   <http://www.tornadoweb.org/>
 * Web.py  0.32  <http://webpy.org/>
 * Beaker  1.3.1 <http://beaker.groovie.org/>