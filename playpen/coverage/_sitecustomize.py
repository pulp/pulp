import atexit
import coverage
import os
import sys
import types

__all__ = ['cov', 'packages', 'root']

root = os.environ.get('PULP_COVERAGE_ROOT', '/srv/pulp_coverage/')

# list of packages/modules to look for when generating coverage
# we could potentially make this dynamic, but the reporting behaves well
# if packages aren't installed, so it's probably easier to just add anything
# we might want to get reporting for
packages = [
    'pulp',
    'pulp_deb',
    'pulp_docker',
    'pulp_openstack',
    'pulp_ostree',
    'pulp_puppet',
    'pulp_python',
    'pulp_rpm',
]

coverage_kwargs = {
    # data_file will be suffixed with hostname and pid to make it unique for this process...
    'data_file': os.path.join(root, 'data'),
    # ...because data_suffix is True.
    'data_suffix': True,
    # only track coverage in pulp packages
    'source': packages
}

cov = coverage.Coverage(**coverage_kwargs)

# these suppress warnings that would otherwise get written every single time
# a python interpreter runs.
cov._warn_no_data = False
cov._warn_unimported_source = False

# start the tracing engine!
cov.start()


# wrap these in a function to ensure they're called in the right order at exit
def exit():
    cov.stop()
    cov.save()
atexit.register(exit)

# expose attributes of this module as a private module for use elsewhere,
# such as in the coverage report generator
_modname = '_pulp_coverage'
_modbases = (types.ModuleType, object)

# instantiate the pulp coverage module type in sys.modules to make it importable
# under the _pulp_coverage name, exposing the attrs in __all__
_modclass = type(_modname, _modbases, {attr: globals()[attr] for attr in __all__})
sys.modules[_modname] = _modclass(_modname)
