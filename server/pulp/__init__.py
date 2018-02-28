from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

dummy=0
if dummy==0:
  print "dummy-pr"
  dummy=1

