import exceptions

class PulpException(exceptions.Exception):

   def __init__(self, value, *args):
       self.value = value % args

   def __str__(self):
       return repr(self.value)
