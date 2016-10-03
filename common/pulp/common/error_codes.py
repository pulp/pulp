from collections import namedtuple
from gettext import gettext as _


Error = namedtuple('Error', ['code', 'message', 'required_fields'])
"""
The error named tuple has 3 components:
code: The 7 character uniquely identifying code for this error, 3 A-Z identifying the module
      followed by 4 numeric characters for the msg id.  All general pulp server errors start
      with PLP
message: The message that will be printed for this error
required_files: A list of required fields for printing the message
"""

# The PLP0000 error is to wrap non-pulp exceptions
PLP0000 = Error("PLP0000", "%(message)s", ['message'])
PLP0001 = Error("PLP0001", _("A general pulp exception occurred"), [])
PLP0008 = Error("PLP0008", _("Error raising error %(code)s.  "
                  "The field [%(field)s] was not included in the error_data."),
                ['code', 'field'])
PLP0009 = Error("PLP0009", _("Missing resource(s): %(resources)s"), ['resources'])
